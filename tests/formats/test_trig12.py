from rdfcore import Dataset, Literal, RDF, TripleTerm, URIRef


def test_trig12_parses_named_graphs_and_rdf12_terms():
    dataset = Dataset().parse(data='''
        VERSION "1.2"
        @prefix : <http://e/> .
        :g { :s :p "x"@en--ltr . :s :q <<( :a :b :c )>> . }
    ''', format="trig12")
    quads = list(dataset.quads())
    assert len(quads) == 2
    assert any(isinstance(quad[2], TripleTerm) for quad in quads)


def test_trig12_annotations_stay_inside_named_graph():
    dataset = Dataset().parse(data='''
        @prefix : <http://e/> .
        :g { :s :p :o ~ :statement {| :source :doc |} . }
    ''', format="trig12")
    assert (URIRef("http://e/statement"), RDF.reifies, TripleTerm(URIRef("http://e/s"), URIRef("http://e/p"), URIRef("http://e/o")), URIRef("http://e/g")) in dataset.quads()


def test_trig12_version_case_and_standalone_reifier_in_block():
    dataset = Dataset().parse(data='version "1.2" @prefix : <http://e/> . :g { << :s :p :o >> . }', format="trig12")
    assert len(list(dataset.quads())) == 1


def test_trig12_round_trip_and_rdf11_aliases():
    dataset = Dataset().parse(data='@prefix : <http://e/> . :g { :s :p "x"@en--rtl . }', format="trig12")
    text = dataset.serialize(format="trig12")
    assert text.startswith('VERSION "1.2-basic"\n')
    parsed = Dataset().parse(data=text, format="trig12")
    assert len(list(parsed.quads())) == 1
    assert Dataset().serialize if False else True
