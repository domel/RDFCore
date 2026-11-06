"""Inventory must expose missing APIs without claiming behavioral parity."""
from benchmarks.audit_api import inventory


def test_inventory_records_missing_shared_and_extension_members():
    report = inventory()
    assert report['rdflib'] == '7.6.0'
    entries = {(row['class'], row['method']): row for row in report['members']}
    assert entries['Graph', 'query']['status'] == 'missing'
    assert entries['Graph', 'add']['status'] == 'present-unverified'
    assert entries['Literal', '__add__']['status'] != 'verified'
    assert report['plugins']
    assert report['exceptions']
