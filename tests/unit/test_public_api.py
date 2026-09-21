import rdfcore


def test_rdf12_plugin_classes_are_part_of_the_public_api():
    expected = {
        "NT12Parser",
        "NQuads12Parser",
        "Turtle12Parser",
        "TriG12Parser",
        "NT12Serializer",
        "NQuads12Serializer",
        "Turtle12Serializer",
        "TriG12Serializer",
    }
    assert expected <= set(rdfcore.__all__)
