import rdflib
import rdfcore


def test_dataset_default_serialization_keeps_named_graph():
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        dataset.add(
            (
                module.URIRef("urn:s"),
                module.URIRef("urn:p"),
                module.Literal("x"),
                module.URIRef("urn:g"),
            )
        )
        result = dataset.serialize()
        parsed = module.Dataset().parse(data=result, format="trig")
        assert len(list(parsed.quads())) == 1
        assert next(parsed.quads())[3] == module.URIRef("urn:g")


def test_dataset_mutation_keyword_arguments():
    for module in (rdflib, rdfcore):
        dataset = module.Dataset()
        key = module.URIRef("urn:g")
        triple = (module.URIRef("urn:s"), module.URIRef("urn:p"), module.Literal("x"))
        dataset.add_graph(g=key)
        assert dataset.add(triple_or_quad=(*triple, key)) is dataset
        assert len(dataset) == 1
        assert dataset.remove(triple_or_quad=triple) is dataset
        assert len(dataset) == 0
        assert dataset.remove_graph(g=key) is dataset
