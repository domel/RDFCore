import operator
from decimal import Decimal
import pytest
import rdflib
import rdfcore


@pytest.mark.parametrize('operation', [operator.neg, operator.pos, abs])
@pytest.mark.parametrize('value,datatype', [(1, None), (-2.5, None), (True, None),
                                          (Decimal('1.5'), None), ('text', None),
                                          ('bad', 'integer'), ('-1.5', 'float'),
                                          ('-2', 'int')])
def test_literal_unary(operation, value, datatype):
    outcomes = []
    for module in (rdflib, rdfcore):
        literal = module.Literal(value, datatype=module.URIRef('http://www.w3.org/2001/XMLSchema#' + datatype) if datatype else None)
        try:
            result = operation(literal)
            outcomes.append((type(result).__name__, str(result), str(result.datatype), result.language, type(result.toPython()).__name__))
        except Exception as exc:
            outcomes.append(type(exc).__name__)
    assert outcomes[0] == outcomes[1]
