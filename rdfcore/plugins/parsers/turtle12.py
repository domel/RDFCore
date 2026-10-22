"""RDF 1.2 Turtle parser for VERSION and directional literals."""

from ...exceptions import BadSyntax
from ...namespace import RDF
from ...term import BNode, TripleTerm, URIRef
from .notation3 import TurtleParser


class Turtle12Parser(TurtleParser):
    rdf_version = "1.2"
    allow_rdf12 = True

    def _term(self, role):
        if self._peek() != "<<":
            return super()._term(role)
        if role == 'datatype':
            raise self._error('datatype must be an IRI')
        if self._peek(1) == '(' and not self.tokens.adjacent(self.index, self.index+1):
            raise self._error('triple term opening delimiter must be contiguous')
        self._next()
        parenthesized = self._accept("(")
        if self._requested_version not in ("auto", "1.2"):
            raise self._error("triple terms require rdf_version='1.2'")
        self._require_version('1.2')
        if parenthesized and self._peek() == '<<':
            raise self._error('triple term subject must be an IRI or blank node')
        if self._accept('['):
            self._expect(']')
            subject = BNode()
        else:
            subject = self._term("triple subject")
        predicate = self._predicate()
        if self._peek() == '(':
            raise self._error('collection is not allowed inside a triple term or reified triple')
        if self._peek() == '[':
            self._next()
            self._expect(']')
            obj = BNode()
        else:
            if parenthesized and self._peek() == '<<' and self._peek(1) != '(':
                raise self._error('reified triple is not allowed inside a triple term')
            obj = self._term('triple object')
        reifier = None
        if not parenthesized and self._accept('~'):
            reifier = self._reifier()
        if parenthesized:
            if self._peek() == ')' and self._peek(1) == '>>' and not self.tokens.adjacent(self.index, self.index+1):
                raise self._error('triple term closing delimiter must be contiguous')
            self._expect(")")
        self._expect(">>")
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise self._error("invalid triple term subject or predicate")
        triple = TripleTerm(subject, predicate, obj)
        if parenthesized:
            if role in ("subject", "predicate"):
                raise self._error("triple term is only allowed as an object")
            return triple
        reifier = BNode() if reifier is None else reifier
        if role == "predicate":
            raise self._error("reifier cannot be used as a predicate")
        self._add((reifier, RDF.reifies, triple))
        if role == "subject":
            self._last_subject_was_reifier = True
        return reifier

    def _subject(self):
        self._last_subject_was_reifier = False
        return super()._subject()

    def _predicate_objects(self, subject):
        while True:
            predicate = self._predicate()
            while True:
                obj = self._object()
                self._add((subject, predicate, obj))
                while self._peek() in ('~', '{|'):
                    self._annotation(subject, predicate, obj)
                if not self._accept(","):
                    break
            if not self._accept(";"):
                break
            while self._accept(";"):
                pass
            if self._peek() in (".", "]", ")", "|}", '}'):
                break

    def _reifier(self):
        if self._peek() == '[':
            self._next()
            self._expect(']')
            return BNode()
        if self._peek() in ('>>', '{|', '~', '.', ',', ';', '|}', '}'):
            return BNode()
        reifier = self._term('reifier')
        if not isinstance(reifier, (URIRef, BNode)):
            raise self._error('reifier must be an IRI or blank node')
        return reifier

    def _annotation(self, subject, predicate, obj):
        self._require_version('1.2')
        reifier = self._reifier() if self._accept('~') else BNode()
        self._add((reifier, RDF.reifies, TripleTerm(subject, predicate, obj)))
        if self._accept("{|"):
            self._predicate_objects(reifier)
            self._expect("|}")


__all__ = ["Turtle12Parser"]
