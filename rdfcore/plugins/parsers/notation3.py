"""Small RDF 1.1 Turtle parser used by the baseline implementation."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from ...exceptions import BadSyntax
from ...parser import Parser
from ...term import BNode, Literal, TripleTerm, URIRef
from ...namespace import RDF
from .ntriples import _unescape


class TurtleParser(Parser):
    rdf_version = "1.1"
    allow_rdf12 = False

    def parse(self, source, sink, **kwargs):
        stream = source.getCharacterStream() or source.getByteStream()
        if stream is None:
            raise BadSyntax("Turtle source has no readable stream")
        self.sink = sink
        self.base = source.publicID or kwargs.get("base")
        self.prefixes = {}
        self.bnodes = {}
        self.tokens = _StreamingTokens(stream)
        self.index = 0
        self._requested_version = kwargs.get("rdf_version", "auto")
        while not self._at_end():
            if self._peek_lower() == "version" or self._peek() == "@version":
                self._directive_version()
            elif self._peek() == "@prefix" or self._peek_lower() == "prefix":
                self._directive_prefix()
            elif self._peek() == "@base" or self._peek_lower() == "base":
                self._directive_base()
            else:
                self._statement()
        return sink

    def _statement(self):
        subject = self._subject()
        if self._accept("."):
            if self._last_subject_is_property_list or getattr(self, "_last_subject_was_reifier", False):
                return
            raise self._error("expected predicate")
        self._predicate_objects(subject)
        self._expect(".")

    def _add(self, triple):
        self.sink.add(triple)

    def _predicate_objects(self, subject):
        while True:
            predicate = self._predicate()
            while True:
                obj = self._object()
                self._add((subject, predicate, obj))
                if not self._accept(","):
                    break
            if not self._accept(";"):
                break
            while self._accept(";"):
                pass
            if self._peek() in (".", "]", ")", "|}"):
                break
            if self._peek() == "}":
                break

    def _subject(self):
        self._last_subject_is_property_list = False
        self._last_subject_is_collection = False
        if self._accept("["):
            node = BNode()
            self._last_subject_is_property_list = True
            if not self._accept("]"):
                self._predicate_objects(node)
                self._expect("]")
            return node
        if self._accept("("):
            self._last_subject_is_collection = True
            return self._collection()
        return self._term("subject")

    def _object(self):
        if self._peek() == "[":
            return self._subject()
        if self._peek() == "(":
            self._next()
            return self._collection()
        return self._term("object")

    def _collection(self):
        if self._accept(")"):
            return RDF.nil
        head = BNode()
        current = head
        while self._peek() != ")":
            item = self._object()
            self._add((current, RDF.first, item))
            if self._peek() == ")":
                self._add((current, RDF.rest, RDF.nil))
            else:
                nxt = BNode()
                self._add((current, RDF.rest, nxt))
                current = nxt
        self._expect(")")
        return head

    def _predicate(self):
        if self._accept("a"):
            return RDF.type
        return self._term("predicate")

    def _term(self, role):
        token = self._next()
        if token is None:
            raise self._error(f"missing {role}")
        if token.startswith("<"):
            if not token.endswith(">"):
                raise self._error("unterminated IRI")
            value = _unescape(token[1:-1], self._line())
            if any(ord(char) <= 0x20 or char in "<>\\^`{}|" for char in value):
                raise self._error("invalid IRI")
            return URIRef(_resolve_iri(self.base or "", value))
        if token.startswith("_:"):
            label = token[2:]
            if not label or label.startswith(('.', '-')) or label.endswith('.') or any(char.isspace() or char in ":;,[](){}<>\"'" for char in label):
                raise self._error("invalid blank node label")
            return self.bnodes.setdefault(token[2:], BNode())
        if token.startswith(('"', "'")):
            lexical = _decode_string(token, self._line())
            lang = None
            datatype = None
            if self._peek() and self._peek().startswith("@"):
                lang = self._next()[1:]
                direction = None
                if "--" in lang:
                    lang, direction = lang.split("--", 1)
                    if not self.allow_rdf12 or self._requested_version == "1.1":
                        raise self._error("directional literal requires RDF 1.2")
                if not re.fullmatch(r"[A-Za-z]+(?:-[A-Za-z0-9]+)*", lang):
                    raise self._error("invalid language tag")
                if direction is not None and direction not in ("ltr", "rtl"):
                    raise self._error("invalid text direction")
            elif self._accept("^^"):
                datatype = self._term("datatype")
                direction = None
            else:
                direction = None
            return Literal(lexical, lang=lang, datatype=datatype, normalize=False, direction=direction)
        if token in ("true", "false"):
            return Literal(token, datatype="http://www.w3.org/2001/XMLSchema#boolean", normalize=False)
        if re.fullmatch(r"[+-]?\d+", token):
            return Literal(token, datatype="http://www.w3.org/2001/XMLSchema#integer", normalize=False)
        if re.fullmatch(r"[+-]?\d*\.\d+", token):
            return Literal(token, datatype="http://www.w3.org/2001/XMLSchema#decimal", normalize=False)
        if re.fullmatch(r"[+-]?(?:\d+\.?(?:\d*)?|\.\d+)[eE][+-]?\d+", token):
            return Literal(token, datatype="http://www.w3.org/2001/XMLSchema#double", normalize=False)
        if ":" in token:
            prefix, local = token.split(":", 1)
            if prefix not in self.prefixes:
                raise self._error(f"unknown prefix {prefix!r}")
            if local.startswith(('.', '-')) or local.endswith('.'):
                raise self._error("invalid prefixed-name local part")
            return URIRef(self.prefixes[prefix] + _decode_pname_local(local, self._line()))
        raise self._error(f"invalid {role} {token!r}")

    def _directive_prefix(self):
        directive = self._next()
        prefix = self._next()
        if prefix is None or not prefix.endswith(":"):
            raise self._error("expected prefix label")
        iri = self._next()
        if iri is None or not iri.startswith("<"):
            raise self._error("expected prefix IRI")
        if not iri.endswith(">"):
            raise self._error("unterminated prefix IRI")
        label = prefix[:-1]
        if label and (label.startswith('.') or label.endswith('.') or not _valid_pname_prefix(label)):
            raise self._error("invalid prefix label")
        self.prefixes[label] = _resolve_iri(self.base or "", _unescape(iri[1:-1], self._line()))
        if directive.lower() == "@prefix":
            self._expect(".")

    def _directive_base(self):
        directive = self._next()
        iri = self._next()
        if iri is None or not iri.startswith("<"):
            raise self._error("expected base IRI")
        if not iri.endswith(">"):
            raise self._error("unterminated base IRI")
        self.base = _resolve_iri(self.base or "", _unescape(iri[1:-1], self._line()))
        if directive.lower() == "@base":
            self._expect(".")

    def _directive_version(self):
        if not self.allow_rdf12:
            raise self._error("VERSION requires the RDF 1.2 Turtle parser")
        directive = self._next()
        token = self._next()
        if token is None or not token.startswith(('"', "'")) or token.startswith(('"""', "'''")):
            raise self._error("VERSION requires a short string")
        version = _decode_string(token, self._line())
        if version not in ("1.1", "1.2-basic", "1.2"):
            raise self._error("invalid RDF version")
        if directive == "@version":
            self._expect(".")

    def _peek(self, offset=0):
        return self.tokens[self.index + offset]

    def _peek_lower(self):
        token = self._peek()
        return token.lower() if token else None

    def _next(self):
        token = self._peek()
        self.index += token is not None
        if token is not None and hasattr(self.tokens, "discard_before"):
            self.tokens.discard_before(self.index)
        return token

    def _accept(self, token):
        if self._peek() == token:
            self.index += 1
            if hasattr(self.tokens, "discard_before"):
                self.tokens.discard_before(self.index)
            return True
        return False

    def _expect(self, token):
        if not self._accept(token):
            raise self._error(f"expected {token!r}")

    def _at_end(self):
        return self._peek() is None

    def _line(self):
        return 1

    def _error(self, message):
        return BadSyntax(f"line {self._line()}: {message}")


Notation3Parser = TurtleParser


def _tokenize(data):
    tokens = []
    index = 0
    punctuation = set(";,[](){}")
    while index < len(data):
        if data[index].isspace() or data[index] == "#":
            if data[index] == "#":
                end = data.find("\n", index)
                index = len(data) if end < 0 else end
            else:
                index += 1
            continue
        if data.startswith("^^", index):
            tokens.append("^^")
            index += 2
            continue
        if data.startswith("<<", index) or data.startswith(">>", index):
            tokens.append(data[index:index + 2])
            index += 2
            continue
        if data.startswith("{|", index) or data.startswith("|}", index):
            tokens.append(data[index:index + 2])
            index += 2
            continue
        if data[index] == "@":
            directive = next((item for item in ("@prefix", "@base") if data[index:].lower().startswith(item)), None)
            if directive and index + len(directive) < len(data) and data[index + len(directive)] in ":<":
                tokens.append(data[index:index + len(directive)])
                index += len(directive)
                continue
        if data[index] in "<>":
            closing = data[index] == "<"
            end = index + 1
            escaped = False
            while end < len(data):
                if not escaped and ((closing and data[end] == ">") or (not closing and data[end] == "<")):
                    end += 1
                    break
                escaped = data[end] == "\\" and not escaped
                if data[end] != "\\":
                    escaped = False
                end += 1
            tokens.append(data[index:end])
            index = end
            continue
        if data[index] in "\"'":
            end = _scan_string(data, index)
            tokens.append(data[index:end])
            index = end
            continue
        if data[index] == "." and not (index + 1 < len(data) and data[index + 1].isdigit()):
            tokens.append(".")
            index += 1
            continue
        if data[index] in ";,[](){}":
            if data[index] != " ":
                tokens.append(data[index])
            index += 1
            continue
        end = index
        while end < len(data) and not data[end].isspace():
            if data[end] in ";,[](){}<>\"'" and not _escaped(data, end):
                break
            if data[end] == "#" and not _escaped(data, end):
                break
            if data.startswith("_:", index) and end > index + 1 and data[end] == ":" and not _escaped(data, end):
                break
            if data[end] == "." and not _escaped(data, end) and (end + 1 == len(data) or data[end + 1].isspace() or data[end + 1] in ";,[](){}#"):
                break
            end += 1
        tokens.append(data[index:end])
        index = end
    return [token for token in tokens if token != " "]


class _StreamingTokens:
    """Lazy Turtle token sequence with only parser look-ahead in memory."""

    def __init__(self, stream):
        from ...tokenizer import TokenReader

        self._tokens = iter(TokenReader(stream))
        self._buffer = []
        self._offset = 0
        self._done = False

    def __getitem__(self, index):
        if index < self._offset:
            raise IndexError("token has already been consumed")
        while self._offset + len(self._buffer) <= index and not self._done:
            try:
                token = next(self._tokens)
            except StopIteration:
                self._done = True
                break
            if token.kind not in ("whitespace", "comment"):
                self._buffer.append(token.value)
        relative = index - self._offset
        return self._buffer[relative] if relative < len(self._buffer) else None

    def discard_before(self, index):
        count = max(0, min(index - self._offset, len(self._buffer)))
        if count:
            del self._buffer[:count]
            self._offset += count


def _read_text_chunks(stream, chunk_size=64 * 1024):
    chunks = []
    while True:
        chunk = stream.read(chunk_size)
        if chunk == b"" or chunk == "":
            break
        if isinstance(chunk, bytes):
            try:
                chunk = chunk.decode("utf-8")
            except UnicodeDecodeError as error:
                raise BadSyntax(str(error)) from error
        chunks.append(chunk)
    return "".join(chunks)


def _decode_string(token, line):
    if len(token) < 2:
        raise BadSyntax(f"line {line}: unterminated string")
    quote = token[0]
    if quote not in "\"'":
        raise BadSyntax(f"line {line}: invalid string")
    if token.startswith(quote * 3):
        if not token.endswith(quote * 3) or len(token) < 6:
            raise BadSyntax(f"line {line}: unterminated string")
        content = token[3:-3]
    else:
        if not token.endswith(quote):
            raise BadSyntax(f"line {line}: unterminated string")
        content = token[1:-1]
    if quote == "'":
        content = content.replace("\\'", "'")
    return _unescape(content, line)


def _scan_string(data, start):
    quote = data[start]
    delimiter = quote * 3 if data.startswith(quote * 3, start) else quote
    index = start + len(delimiter)
    while index < len(data):
        if data.startswith(delimiter, index) and not _escaped(data, index):
            return index + len(delimiter)
        index += 1
    return len(data)


def _escaped(data, index):
    count = 0
    index -= 1
    while index >= 0 and data[index] == "\\":
        count += 1
        index -= 1
    return bool(count % 2)


def _decode_pname_local(value, line):
    result = []
    index = 0
    allowed = "_~.-!$&'()*+,;=/?#@%"
    while index < len(value):
        if value[index] == "\\":
            if index + 1 >= len(value) or value[index + 1] not in allowed:
                raise BadSyntax(f"line {line}: invalid prefixed-name escape")
            result.append(value[index + 1])
            index += 2
        else:
            if value[index] == "%":
                if index + 2 >= len(value) or not re.fullmatch(r"[0-9A-Fa-f]{2}", value[index + 1:index + 3]):
                    raise BadSyntax(f"line {line}: invalid percent escape")
            elif value[index].isascii() and not (value[index].isalnum() or value[index] in "_:-."):
                raise BadSyntax(f"line {line}: invalid prefixed-name character")
            result.append(value[index])
            index += 1
    return "".join(result)


def _valid_pname_prefix(value):
    return all(not char.isspace() and (not char.isascii() or char.isalnum() or char in "_-.") for char in value)


def _resolve_iri(base, value):
    """Resolve an IRI reference without losing empty URI path segments/fragments."""
    if not base:
        return value
    if value.endswith("#"):
        return _resolve_iri(base, value[:-1]) + "#"
    base_parts = urlsplit(base)
    if "//" not in base_parts.path:
        return urljoin(base, value)
    marker = "__rdf_empty_path_segment__"
    protected = urlunsplit((
        base_parts.scheme,
        base_parts.netloc,
        base_parts.path.replace("//", f"/{marker}/"),
        base_parts.query,
        base_parts.fragment,
    ))
    return urljoin(protected, value).replace(f"/{marker}/", "//")


def _remove_dot_segments(path):
    output = []
    for segment in path.split("/"):
        if segment == ".":
            continue
        if segment == "..":
            if len(output) > 1 or (output and output[0]):
                output.pop()
            continue
        output.append(segment)
    result = "/".join(output)
    return result or "/"
