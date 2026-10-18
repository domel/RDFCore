"""RDF/XML 1.1 and explicit 1.2 serializers, with no runtime RDFLib.

1.2 targets WD-rdf12-xml-20261009. Reifier relationships are serialized
explicitly as rdf:reifies properties; no assertion is inferred from them.
Output ordering and namespace prefixes are not RDF canonicalization.
"""
from xml.sax.saxutils import escape, quoteattr

from ...serializer import Serializer
from ...term import BNode, Literal, TripleTerm, URIRef
from ..parsers.rdfxml import RDF, XML, ITS, is_ncname, CORE, OLD


def _xml(value):
    value = str(value)
    if any(not (c in '\t\n\r' or 0x20 <= ord(c) <= 0xD7FF
                or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF)
           for c in value):
        raise ValueError('term contains a character forbidden in XML 1.0')
    return value


class XMLSerializer(Serializer):
    rdf_version = '1.1'
    encoding = 'utf-8'

    def serialize(self, stream=None, base=None, encoding=None, rdf_version='auto', **kwargs):
        from ...rdf_version import validate_rdf_version
        requested = validate_rdf_version(rdf_version)
        self._output_version = self.rdf_version if requested == 'auto' else requested
        if self.rdf_version == '1.1' and self._output_version != '1.1':
            raise ValueError('select xml12 for RDF 1.2 output')
        self.namespaces = {RDF: 'rdf'}
        self.bnodes = {}
        triples = list(self.store.triples((None, None, None)))
        for triple in triples:
            self._check(triple)
        body = ''.join(self._node(subject, predicate, obj) for subject, predicate, obj in triples)
        declarations = ''.join(' xmlns:'+prefix+'='+quoteattr(_xml(ns)) for ns, prefix in self.namespaces.items())
        if self._output_version != '1.1':
            declarations += ' xmlns:its='+quoteattr(ITS)+' rdf:version='+quoteattr(self._output_version)+' its:version="2.0"'
        if 'xml_base' in kwargs:
            declarations += ' xml:base='+quoteattr(_xml(kwargs['xml_base']))
        elif base:
            declarations += ' xml:base='+quoteattr(_xml(base))
        # RDFLib 7.6.0's XML11 writer ignores the encoding argument and
        # uses its encoding attribute. XML12 retains explicit codec support.
        codec = self.encoding if self.rdf_version == '1.1' else encoding or self.encoding
        value = '<?xml version="1.0" encoding='+quoteattr(codec)+'?>\n<rdf:RDF'+declarations+'>\n'+body+'</rdf:RDF>\n'
        if stream is None:
            return value.encode(codec) if encoding else value
        try:
            stream.write(value.encode(codec))
        except TypeError:
            stream.write(value)
        # RDFLib's XMLSerializer.serialize returns None for supplied streams.
        return None

    def _check(self, triple, depth=0):
        if depth > 128: raise ValueError('triple term nesting exceeds supported depth')
        subject, predicate, obj = triple
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise ValueError('RDF/XML requires a resource subject and IRI predicate')
        self._qname(predicate)
        if isinstance(obj, TripleTerm):
            if self._output_version != '1.2': raise ValueError('triple terms cannot be serialized as RDF '+self._output_version)
            self._check(tuple(obj), depth+1)
        elif isinstance(obj, Literal):
            if obj.direction and self._output_version == '1.1':
                raise ValueError('directional literals require RDF/XML 1.2')
        elif not isinstance(obj, (URIRef, BNode)):
            raise ValueError('unsupported RDF/XML object')

    def _qname(self, iri):
        value = _xml(iri)
        excluded = CORE | OLD | {'Description', 'li'}
        if self.rdf_version == '1.2': excluded |= {'version', 'annotation', 'annotationNodeID'}
        if value.startswith(RDF) and value[len(RDF):] in excluded:
            raise ValueError('predicate cannot be represented in RDF/XML: '+value)
        # Choose the longest NCName suffix, as RDFLib's split_uri does.
        for index in range(1, len(value)):
            if is_ncname(value[index:]):
                ns, local = value[:index], value[index:]
                if ns not in self.namespaces:
                    self.namespaces[ns] = 'ns'+str(len(self.namespaces))
                return self.namespaces[ns]+':'+local
        raise ValueError('predicate has no XML QName representation: '+value)

    def _identity(self, term, subject=False):
        if isinstance(term, URIRef):
            return ' rdf:'+('about' if subject else 'resource')+'='+quoteattr(_xml(term))
        if term not in self.bnodes:
            self.bnodes[term] = 'b'+str(len(self.bnodes))
        return ' rdf:nodeID='+quoteattr(self.bnodes[term])

    def _node(self, subject, predicate, obj):
        return '  <rdf:Description'+self._identity(subject, True)+'>\n'+self._property(predicate, obj)+'  </rdf:Description>\n'

    def _property(self, predicate, obj):
        name = self._qname(predicate)
        if isinstance(obj, TripleTerm):
            content = self._node(*obj)
            return '    <'+name+' rdf:parseType="Triple">\n'+content+'    </'+name+'>\n'
        if isinstance(obj, (URIRef, BNode)):
            return '    <'+name+self._identity(obj)+'/>\n'
        attrs = ''
        if obj.language:
            attrs += ' xml:lang='+quoteattr(_xml(obj.language))
            if obj.direction: attrs += ' its:dir='+quoteattr(obj.direction)
        elif obj.datatype:
            attrs += ' rdf:datatype='+quoteattr(_xml(obj.datatype))
        content = escape(_xml(obj)).replace('\r', '&#13;')
        return '    <'+name+attrs+'>'+content+'</'+name+'>\n'


class XML12Serializer(XMLSerializer):
    rdf_version = '1.2'


XML11Serializer = XMLSerializer
RDFXMLSerializer = XMLSerializer
RDFXML12Serializer = XML12Serializer
