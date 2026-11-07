from itertools import count


from unittest.mock import patch


def observe(module, size, operation, key=0, shape="normal", store=None):
    graph = module.Graph(**({"store": store} if store is not None else {}))
    head = module.URIRef("urn:list") if shape != "nil" else module.RDF.nil
    serial = count()
    factory = lambda: module.BNode("cell%d" % next(serial))
    with patch.object(module.collection, "BNode", factory):
        collection = module.collection.Collection(
            graph, head, [module.Literal(str(i)) for i in range(size)]
        )
        if shape == "unterminated":
            graph.remove((collection._end(), module.RDF.rest, None))
        elif shape == "missing-first":
            graph.remove((head, module.RDF.first, None))
        elif shape == "false-first":
            graph.set((head, module.RDF.first, module.Literal("")))
        elif shape == "metadata":
            graph.add((head, module.URIRef("urn:label"), module.Literal("keep")))

        def run():
            if operation == "get":
                return collection[key]
            if operation == "set":
                return collection.__setitem__(key, module.Literal("new"))
            if operation == "delete":
                return collection.__delitem__(key)
            if operation == "container":
                return collection._get_container(key)
            if operation == "index":
                return collection.index(module.Literal(str(key)))
            if operation == "append":
                return collection.append(module.Literal("new"))
            if operation == "iadd":
                return collection.__iadd__(
                    [module.Literal("new"), module.Literal("new")]
                )
            if operation == "empty-iadd":
                return collection.__iadd__([])
            if operation == "invalid-iadd":
                return collection.__iadd__(None)
            if operation == "clear":
                collection.clear()
                return collection.clear()
            if operation == "n3":
                return collection.n3()
            if operation == "iterate":
                return tuple(collection)
            return collection._end()

        def encode(value):
            if value is collection:
                return "self"
            if isinstance(value, tuple):
                return tuple(encode(item) for item in value)
            if isinstance(value, (module.URIRef, module.BNode, module.Literal)):
                return (type(value).__name__, value.n3())
            return (type(value).__name__, value)

        try:
            outcome = ("return", encode(run()))
        except Exception as error:
            outcome = ("error", type(error).__name__, str(error))
        triples = sorted(tuple(encode(term) for term in triple) for triple in graph)
        return outcome, triples
