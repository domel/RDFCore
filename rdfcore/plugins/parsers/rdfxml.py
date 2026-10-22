"""Secure stdlib RDF/XML plugins.

The explicit 1.2 plugin targets WD-rdf12-xml-20261009 (sections 3.1,
5 and 6); Editor's Draft inspected 2026-10-17. The detailed Triple
production and example 22 take precedence over its inconsistent summary.
This is a tree parser, not a bounded-memory streaming implementation.
DTD declarations are deliberately forbidden, including internal subsets.
"""
from pathlib import Path
import codecs
import re
from urllib.parse import urldefrag, urljoin
from xml.dom import minidom, Node
from xml.parsers import expat
from xml.sax import SAXParseException

from ...parser import Parser
from ...exceptions import ParserError
from ..._datatype_xml import _restricted, xml11_source
from ..._iri_reference import is_iri_reference
from ...term import BNode, Literal, TripleTerm, URIRef

RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
XML = 'http://www.w3.org/XML/1998/namespace'
ITS = 'http://www.w3.org/2005/11/its'
CORE = {'RDF', 'ID', 'about', 'parseType', 'resource', 'nodeID', 'datatype'}
OLD = {'aboutEach', 'aboutEachPrefix', 'bagID'}
_UTF32_PREFIXES = (b'\x00\x00\xfe\xff', b'\xff\xfe\x00\x00',
                   b'\x00\x00\x00<', b'<\x00\x00\x00')


def is_ncname(value):
    # XML 1.0 fifth edition, Namespaces NCName (also XML 1.1 names).
    def start(c):
        n = ord(c)
        return c == '_' or 'A' <= c <= 'Z' or 'a' <= c <= 'z' or any(
            lo <= n <= hi for lo, hi in ((0xC0, 0xD6), (0xD8, 0xF6),
            (0xF8, 0x2FF), (0x370, 0x37D), (0x37F, 0x1FFF),
            (0x200C, 0x200D), (0x2070, 0x218F), (0x2C00, 0x2FEF),
            (0x3001, 0xD7FF), (0xF900, 0xFDCF), (0xFDF0, 0xFFFD),
            (0x10000, 0xEFFFF)))
    return bool(value) and start(value[0]) and all(
        start(c) or c in '-.' or '0' <= c <= '9' or ord(c) == 0xB7
        or 0x300 <= ord(c) <= 0x36F or 0x203F <= ord(c) <= 0x2040
        for c in value[1:])


class _Locator:
    def getSystemId(self): return None
    def getLineNumber(self): return None
    def getColumnNumber(self): return None


def _error(message):
    raise SAXParseException(message, None, _Locator())


def _reserved_xml_name(element):
    return (element.prefix or element.localName or element.nodeName).lower().startswith('xml')


def _elements(element, strict=False):
    return [child for child in element.childNodes if child.nodeType == Node.ELEMENT_NODE
            and not (strict and _reserved_xml_name(child))]


def _text(element):
    return ''.join(c.data for c in element.childNodes if c.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))


def _whitespace(element, strict=False):
    # RDFLib's XML11 handler accepts broader Unicode whitespace. XML12
    # follows production ws, which only permits XML's four S characters.
    text = _text(element)
    if (text.strip(' \t\r\n') if strict else text.strip()):
        _error('unexpected text between RDF elements')


def _xml12_transport(data):
    """Decode XML transport without changing the legacy Expat byte contract.

    XML 1.1 Second Edition appendix F and §§2.2/2.11. DTD processing
    remains disabled in the guard, before any RDF statement is emitted.
    """
    if isinstance(data, bytes):
        encoding = None
        for prefix, codec in ((b'\x00\x00\xfe\xff', 'utf-32'),
                              (b'\xff\xfe\x00\x00', 'utf-32'),
                              (b'\x00\x00\x00<', 'utf-32-be'),
                              (b'<\x00\x00\x00', 'utf-32-le'),
                              (b'\xff\xfe', 'utf-16'), (b'\xfe\xff', 'utf-16'),
                              (b'\x00<\x00?', 'utf-16-be'),
                              (b'<\x00?\x00', 'utf-16-le')):
            if data.startswith(prefix):
                encoding = codec
                break
        if encoding:
            decoded = data.decode(encoding)
            declaration = re.match(r'\ufeff?<\?xml\s+[^?]*\?>', decoded)
            declared = re.search(r'encoding\s*=\s*[\'"]([^\'"]+)[\'"]', declaration[0]) if declaration else None
            if declared:
                actual = encoding.split('-')[1]
                expected = codecs.lookup(declared[1]).name
                if expected not in {'utf-'+actual, 'utf-'+actual+'-le', 'utf-'+actual+'-be'}:
                    raise ValueError('XML encoding declaration does not match byte transport')
                if expected.endswith('-le') and data[:4] in {b'\x00\x00\xfe\xff', b'\x00\x00\x00<', b'\xfe\xff\x00<', b'\x00<\x00?'}:
                    raise ValueError('XML encoding declaration has the wrong byte order')
                if expected.endswith('-be') and data[:4] in {b'\xff\xfe\x00\x00', b'<\x00\x00\x00', b'\xff\xfe<\x00', b'<\x00?\x00'}:
                    raise ValueError('XML encoding declaration has the wrong byte order')
            data = decoded
        else:
            # Leave XML 1.0 bytes to Expat, including encoding validation.
            declaration = re.match(br'<\?xml\s+[^?]*\?>', data[3:] if data.startswith(b'\xef\xbb\xbf') else data)
            if declaration and re.search(br'version\s*=\s*[\'"]1\.1[\'"]', declaration[0]):
                codec = re.search(br'encoding\s*=\s*[\'"]([^\'"]+)[\'"]', declaration[0])
                data = data.decode(codec[1].decode('ascii') if codec else 'utf-8-sig')
    if isinstance(data, str) and re.match(r'\ufeff?<\?xml\s+version\s*=\s*[\'"]1\.1[\'"]', data):
        # XML 1.1 §2.11 makes these fatal in the declaration itself, where
        # normalizing them before Expat would otherwise hide invalid input.
        declaration = data.split('?>', 1)[0]
        if '\x85' in declaration or '\u2028' in declaration:
            raise ValueError('XML 1.1 line separators are forbidden in the XML declaration')
        return xml11_source(data)
    return data, {}


class RDFXMLParser(Parser):
    rdf_version = '1.1'

    def parse(self, source, sink, **kwargs):
        strict = kwargs.get('strict', False)
        if type(strict) is not bool:
            raise ValueError('strict must be a boolean')
        self.compatibility = self.rdf_version == '1.1' and not strict
        self.legacy_w3c = kwargs.get('legacy_w3c', False)
        if type(self.legacy_w3c) is not bool:
            raise ValueError('legacy_w3c must be a boolean')
        stream = source.getCharacterStream()
        if stream is None:
            stream = source.getByteStream()
        if stream is None:
            _error('RDF/XML source has no readable stream')
        # Expat recognizes declarations regardless of encoding or chunk boundaries.
        guard = expat.ParserCreate()
        def forbid(*args):
            _error('DTD declarations and external entities are forbidden')
        guard.StartDoctypeDeclHandler = forbid
        guard.ExternalEntityRefHandler = forbid
        chunks = []
        depth = 0
        def start(*args):
            nonlocal depth
            depth += 1
            if depth > 256:
                _error('XML nesting exceeds the supported depth of 256')
        def end(*args):
            nonlocal depth
            depth -= 1
        guard.StartElementHandler = start
        guard.EndElementHandler = end
        self.restore = {}
        self.xml11 = False
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if self.rdf_version == '1.1':
                    guard.Parse(chunk, False)
            data = (b'' if not chunks or isinstance(chunks[0], bytes) else '').join(chunks)
            if self.rdf_version == '1.2':
                try:
                    data, self.restore = _xml12_transport(data)
                except (UnicodeError, LookupError, ValueError) as exc:
                    _error(str(exc))
                self.xml11 = isinstance(data, str) and bool(re.match(
                    r'\ufeff?<\?xml\s+version\s*=\s*[\'"]1\.1[\'"]', data))
                for offset in range(0, len(data), 65536):
                    guard.Parse(data[offset:offset+65536], False)
            guard.Parse(b'', True)
            dom = minidom.parseString(data)
        except expat.ExpatError as exc:
            if self.rdf_version == '1.1' and chunks and isinstance(chunks[0], bytes):
                prefix = b''.join(chunks[:4])[:4]
                if prefix.startswith(_UTF32_PREFIXES):
                    _error('UTF-32 byte input is unsupported by the legacy XML parser; '
                           'decode to text or select xml12')
            _error(str(exc))
        self.bnodes = {}
        self.ids = set()
        self.preserve_bnode_ids = kwargs.get('preserve_bnode_ids', False)
        base = getattr(source, 'publicID', None) or getattr(source, 'location', None) or ''
        if base and not str(base).split(':', 1)[0] in ('http', 'https', 'urn', 'file'):
            base = Path(base).absolute().as_uri()
        # Explicit recovery for pre-version-announcement W3C fixtures. An
        # actual declaration still overrides this fallback, including 1.1.
        version = '1.2' if self.legacy_w3c and self.rdf_version == '1.2' else '1.1'
        context = (str(base), None, None, version)
        try:
            root = dom.documentElement
            if self.rdf_version == '1.2' and _reserved_xml_name(root):
                _error('reserved XML name cannot be an RDF document element')
            for element in dom.getElementsByTagName('*'):
                for attr in element.attributes.values():
                    if attr.namespaceURI == 'http://www.w3.org/2000/xmlns/':
                        if self.rdf_version == '1.2' and any(
                                _restricted(ord(char)) for char in (attr.value or '').translate(self.restore)):
                            _error('restricted XML characters cannot occur in a namespace IRI')
                        self._iri((attr.value or '').translate(self.restore))
                        target = getattr(sink, 'graph', getattr(sink, 'dataset', sink))
                        if hasattr(target, 'bind'):
                            target.bind('' if attr.name == 'xmlns' else attr.localName, URIRef(attr.value))
            if self._name(root) == RDF+'RDF':
                context, attrs = self._context(root, context)
                if attrs and not self.compatibility:
                    _error('invalid attributes on rdf:RDF')
                _whitespace(root, self.rdf_version == '1.2')
                for child in _elements(root, self.rdf_version == '1.2'):
                    self._node(child, context, sink.add)
            else:
                self._node(root, context, sink.add)
        finally:
            dom.unlink()

    def _name(self, element):
        if not element.namespaceURI:
            if self.compatibility:
                return element.localName or element.nodeName
            _error('RDF elements require a namespace')
        return element.namespaceURI + element.localName

    def _context(self, element, parent):
        base, lang, direction, version = parent
        attrs = {}
        for attr in element.attributes.values():
            ns = attr.namespaceURI
            if ns == 'http://www.w3.org/2000/xmlns/':
                continue
            value = attr.value.translate(self.restore)
            if ns == XML:
                if attr.localName == 'base': base = urldefrag(self._iri(value, base))[0]
                if attr.localName == 'lang': lang = value or None
                continue
            if (self.rdf_version == '1.2' and attr.prefix
                    and attr.prefix.lower().startswith('xml')):
                continue
            if not ns:
                if attr.name.lower().startswith('xml'): continue
                unqualified = {'ID', 'about', 'parseType', 'resource', 'type'}
                if self.compatibility:
                    key = RDF+attr.name if attr.name in unqualified else attr.name
                elif attr.name not in unqualified | {'version'}:
                    _error('unqualified RDF attribute: '+attr.name)
                else:
                    key = RDF+attr.name
            else:
                key = ns+attr.localName
            if key in attrs: _error('duplicate RDF attribute: '+key)
            attrs[key] = value
        if self.rdf_version == '1.2':
            version = attrs.pop(RDF+'version', version)
            if version not in {'1.1', '1.2-basic', '1.2'}:
                _error('unsupported RDF version: '+version)
            if version != '1.1':
                direction = attrs.pop(ITS+'dir', direction) or None
                if direction not in (None, 'ltr', 'rtl'): _error('invalid its:dir')
                attrs.pop(ITS+'version', None)
        return (base, lang, direction, version), attrs

    def _bnode(self, label):
        if not is_ncname(label): _error('rdf:nodeID value is not a valid NCName')
        if label not in self.bnodes:
            self.bnodes[label] = BNode(label) if self.preserve_bnode_ids else BNode()
        return self.bnodes[label]

    def _iri(self, value, base=None):
        # Validate before resolution too: urljoin may strip control characters.
        # URIRef and the legacy XML11 compatibility path stay permissive.
        if self.rdf_version == '1.2' and not is_iri_reference(value):
            _error('invalid RDF/XML IRI reference')
        resolved = value if base is None else urljoin(base, value)
        if self.rdf_version == '1.2' and not is_iri_reference(resolved):
            _error('invalid resolved RDF/XML IRI')
        return URIRef(resolved)

    def _id(self, value, context, property_id=False):
        if not is_ncname(value): _error('rdf:ID value is not a valid NCName')
        key = self._iri('#'+value, context[0])
        if self.compatibility and property_id:
            return key
        if key in self.ids:
            if self.compatibility:
                raise ParserError('two elements cannot use the same ID: '+str(key))
            _error('duplicate rdf:ID')
        self.ids.add(key)
        return key

    def _literal(self, value, context, datatype=None):
        value = value.translate(self.restore)
        if datatype is not None:
            return Literal(value, datatype=self._iri(datatype, None if self.compatibility else context[0]))
        if self.rdf_version == '1.2' and context[3] == '1.1' and context[1] and context[2]:
            _error('directional literals cannot be emitted in RDF 1.1')
        return Literal(value, lang=context[1], direction=context[2] if context[1] else None)

    def _valid_name(self, name, kind, version=None):
        excluded = CORE | OLD
        if self.rdf_version == '1.2' and version != '1.1': excluded |= {'version', 'annotation', 'annotationNodeID'}
        if kind != 'node': excluded |= {'Description'}
        if kind != 'property': excluded |= {'li'}
        if name.startswith(RDF) and name[len(RDF):] in excluded:
            _error('Invalid '+kind+' URI: '+name)

    def _attributes(self, subject, attrs, context, emit, empty_property=False):
        for key, value in attrs.items():
            self._valid_name(key, 'attribute', context[3])
            raw_type = self.compatibility and empty_property
            obj = self._iri(value, None if raw_type else context[0]) if key == RDF+'type' else self._literal(value, context)
            emit((subject, URIRef(urljoin(context[0], key)) if self.compatibility else URIRef(key), obj))

    def _node(self, element, parent, emit):
        context, attrs = self._context(element, parent)
        name = self._name(element)
        if self.compatibility:
            name = urljoin(context[0], name)
        self._valid_name(name, 'node', context[3])
        identity = [key for key in ('about', 'ID', 'nodeID') if RDF+key in attrs]
        if len(identity) > 1: _error('conflicting node identity attributes')
        subject = BNode()
        if identity:
            key = identity[0]
            value = attrs.pop(RDF+key)
            subject = self._id(value, context) if key == 'ID' else self._bnode(value) if key == 'nodeID' else self._iri(value, context[0])
        if name != RDF+'Description': emit((subject, URIRef(RDF+'type'), URIRef(name)))
        self._attributes(subject, attrs, context, emit)
        self._properties(element, subject, context, emit)
        return subject

    def _properties(self, element, subject, context, emit):
        _whitespace(element, self.rdf_version == '1.2')
        counter = 0
        for child in _elements(element, self.rdf_version == '1.2'):
            name = self._name(child)
            if name == RDF+'li':
                counter += 1
                name = RDF+'_'+str(counter)
            self._property(child, subject, URIRef(name), context, emit)

    def _property(self, element, subject, predicate, parent, emit):
        context, attrs = self._context(element, parent)
        if self.compatibility:
            predicate = URIRef(urljoin(context[0], predicate))
        self._valid_name(str(predicate), 'property', context[3])
        identifier = attrs.pop(RDF+'ID', None)
        reified = self._id(identifier, context, property_id=True) if identifier is not None else None
        annotation = attrs.pop(RDF+'annotation', None) if self.rdf_version == '1.2' else None
        annotation_node = attrs.pop(RDF+'annotationNodeID', None) if self.rdf_version == '1.2' else None
        if annotation is not None or annotation_node is not None:
            if context[3] != '1.2': _error('annotations require rdf:version="1.2"')
            if annotation is not None and annotation_node is not None: _error('conflicting annotation identifiers')
        parse_type = attrs.pop(RDF+'parseType', None)
        children = _elements(element, self.rdf_version == '1.2')
        if parse_type is not None:
            if attrs: _error('property attributes not allowed with rdf:parseType')
            if parse_type == 'Resource':
                obj = BNode()
                self._properties(element, obj, context, emit)
            elif parse_type == 'Collection':
                _whitespace(element, self.rdf_version == '1.2')
                values = [self._node(c, context, emit) for c in children]
                obj = BNode() if values else URIRef(RDF+'nil')
                cell = obj
                for index, value in enumerate(values):
                    tail = BNode() if index+1 < len(values) else URIRef(RDF+'nil')
                    emit((cell, URIRef(RDF+'first'), value))
                    emit((cell, URIRef(RDF+'rest'), tail))
                    cell = tail
            elif parse_type == 'Triple' and self.rdf_version == '1.2':
                if context[3] != '1.2': _error('triple terms require rdf:version="1.2"')
                if reified is not None or annotation is not None or annotation_node is not None:
                    _error('Triple production permits only rdf:parseType')
                _whitespace(element, self.rdf_version == '1.2')
                triples = set()
                for child in children: self._node(child, context, triples.add)
                if len(triples) != 1: _error('Triple content must generate exactly one triple')
                obj = TripleTerm(*next(iter(triples)))
            else:
                obj = Literal(self._xml_literal(element), datatype=URIRef(RDF+'XMLLiteral'))
        else:
            resource = attrs.pop(RDF+'resource', None)
            node = attrs.pop(RDF+'nodeID', None)
            datatype = attrs.pop(RDF+'datatype', None)
            if sum(v is not None for v in (resource, node, datatype)) > 1:
                _error('conflicting property object attributes')
            if children:
                if attrs or resource is not None or node is not None or datatype is not None or len(children) != 1:
                    _error('invalid resource property content')
                _whitespace(element, self.rdf_version == '1.2')
                obj = self._node(children[0], context, emit)
            elif resource is not None or node is not None or attrs:
                if _text(element) and not self.compatibility: _error('resource property must be empty')
                if datatype is not None: _error('datatype and property attributes cannot be combined')
                obj = self._iri(resource, context[0]) if resource is not None else self._bnode(node) if node is not None else BNode()
                self._attributes(obj, attrs, context, emit, empty_property=True)
            else:
                obj = self._literal(_text(element), context, datatype)
        triple = (subject, predicate, obj)
        emit(triple)
        if reified is not None:
            emit((reified, URIRef(RDF+'type'), URIRef(RDF+'Statement')))
            for key, value in zip(('subject', 'predicate', 'object'), triple):
                emit((reified, URIRef(RDF+key), value))
        if annotation is not None or annotation_node is not None:
            reifier = self._iri(annotation, context[0]) if annotation is not None else self._bnode(annotation_node)
            emit((reifier, URIRef(RDF+'reifies'), TripleTerm(*triple)))

    def _xml_literal(self, element):
        # Preserve source prefixes and add inherited declarations where needed,
        # matching RDFLib's exclusive namespace handling for common XML literals.
        def clone(node, scope):
            if self.rdf_version == '1.1' and node.nodeType in (Node.COMMENT_NODE, Node.PROCESSING_INSTRUCTION_NODE):
                return None
            if node.nodeType == Node.CDATA_SECTION_NODE:
                return node.ownerDocument.createTextNode(node.data)
            result = node.cloneNode(False)
            if node.nodeType == Node.ELEMENT_NODE:
                scope = dict(scope)
                if self.rdf_version == '1.1':
                    for attr in list(result.attributes.values()):
                        if attr.name == 'xmlns' or attr.prefix == 'xmlns':
                            result.removeAttribute(attr.name)
                used = [(node.prefix or '', node.namespaceURI)]
                used += [(a.prefix, a.namespaceURI) for a in node.attributes.values()
                         if a.prefix and a.prefix != 'xmlns']
                for prefix, ns in used:
                    # The reference XML11 SAX handler omits default namespace
                    # undeclarations. Keep that legacy lexical contract out of
                    # XML12, where the undeclaration preserves the XML infoset.
                    if self.rdf_version == '1.1' and not ns:
                        continue
                    if (ns or prefix == '') and scope.get(prefix) != ns:
                        result.setAttribute('xmlns'+(':'+prefix if prefix else ''), ns or '')
                        scope[prefix] = ns
            for child in node.childNodes:
                copied = clone(child, scope)
                if copied is not None:
                    result.appendChild(copied)
            if self.legacy_w3c and node.nodeType == Node.ELEMENT_NODE and not node.childNodes:
                # DOM serialization, not a regex over markup or attribute data.
                # This is empty-element expansion, not a general C14N engine.
                result.appendChild(node.ownerDocument.createTextNode(''))
            return result
        fragment = element.ownerDocument.createDocumentFragment()
        for child in element.childNodes:
            copied = clone(child, {'xml': XML})
            if copied is not None:
                fragment.appendChild(copied)
        if self.rdf_version == '1.1':
            # RDFLib reparses its generated XMLLiteral text, normalizing CR in
            # text content. Do not normalize attribute values or XML12 here.
            if not self.legacy_w3c:
                fragment.normalize()
            def normalize_text(node):
                if node.nodeType == Node.TEXT_NODE:
                    node.data = node.data.replace('\r\n', '\n').replace('\r', '\n')
                for child in node.childNodes:
                    normalize_text(child)
            normalize_text(fragment)
        value = ''.join(child.toxml() for child in fragment.childNodes)
        references = {key: '&#'+str(ord(char))+';' for key, char in self.restore.items()}
        if self.xml11:
            references.update({ord(char): '&#'+str(ord(char))+';' for char in value
                               if _restricted(ord(char)) or char in '\r\x85\u2028'})
        return value.translate(references)


class RDFXML12Parser(RDFXMLParser):
    rdf_version = '1.2'


RDFXML11Parser = RDFXMLParser
