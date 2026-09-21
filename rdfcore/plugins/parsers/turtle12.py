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
        self._next()
        parenthesized = self._accept("(")
        if self._requested_version not in ("auto", "1.2"):
            raise self._error("triple terms require rdf_version='1.2'")
        subject = self._term("triple subject")
        predicate = self._term("triple predicate")
        obj = self._object()
        if parenthesized:
            self._expect(")")
        self._expect(">>")
        if not isinstance(subject, (URIRef, BNode)) or not isinstance(predicate, URIRef):
            raise self._error("invalid triple term subject or predicate")
        triple = TripleTerm(subject, predicate, obj)
        if parenthesized:
            if role in ("subject", "predicate"):
                raise self._error("triple term is only allowed as an object")
            return triple
        reifier = BNode()
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
                if self._peek() == "~":
                    self._annotation(subject, predicate, obj)
                if not self._accept(","):
                    break
            if not self._accept(";"):
                break
            while self._accept(";"):
                pass
            if self._peek() in (".", "]", ")", "|}"):
                break

    def _annotation(self, subject, predicate, obj):
        self._expect("~")
        if self._peek() == "{|":
            reifier = BNode()
        else:
            reifier = self._term("reifier")
        self._add((reifier, RDF.reifies, TripleTerm(subject, predicate, obj)))
        if self._accept("{|"):
            self._predicate_objects(reifier)
            self._expect("|}")


__all__ = ["Turtle12Parser"]
