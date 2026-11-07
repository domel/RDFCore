"""ConjunctiveGraph parser dispatch."""

import rdflib
import rdfcore


def test_context_parser_override():
    for module in (rdflib, rdfcore):
        calls = []

        class Custom(module.Graph):
            def parse(self, source=None, **options):
                calls.append(source)
                return super().parse(source=source, **options)

        graph = module.ConjunctiveGraph()
        context = Custom(store=graph.store)
        graph.default_context = context
        assert graph.parse(data="<urn:s> <urn:p> <urn:o> .", format="turtle") is graph
        assert len(calls) == 1
        assert hasattr(calls[0], "getByteStream")
        assert len(context) == 1
