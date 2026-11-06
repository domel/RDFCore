"""Inventory must expose missing APIs without claiming behavioral parity."""
from benchmarks.audit_api import inventory


def test_inventory_records_missing_shared_and_extension_members():
    report = inventory()
    assert report['rdflib'] == '7.6.0'
    entries = {(row['class'], row['method']): row for row in report['members']}
    assert entries['Graph', 'query']['status'] == 'missing'
    assert entries['Graph', 'add']['status'] == 'verified-scoped'
    assert entries['Literal', '__add__']['status'] != 'verified'
    assert report['plugins']
    assert report['exceptions']


def test_inventory_sees_instance_fields_and_cites_executable_scope():
    report = inventory()
    entries = {(row['class'], row['method']): row for row in report['members']}
    for key in [('Literal', 'datatype'), ('Literal', 'value'), ('Graph', 'identifier'), ('Graph', 'store')]:
        assert entries[key]['status'] != 'missing'
    assert entries['Graph', 'add']['status'] == 'verified-scoped'
    assert entries['Graph', 'add']['evidence']
    assert report['classes']


def test_scoped_evidence_paths_and_public_green_rows_are_explicit():
    import re
    from pathlib import Path
    from benchmarks.api_evidence import SCOPES
    for evidence in SCOPES.values():
        assert evidence['scope']
        for path in evidence['tests']:
            source = Path(path).read_text()
            assert 'import rdflib' in source and 'import rdfcore' in source
    for line in Path('Compare_with_rdflib.md').read_text().splitlines():
        if not line.startswith('|'):
            continue
        cells = [value.strip() for value in line.strip('|').split('|')]
        if len(cells) >= 4 and any('✅' in value for value in cells[2:-1]):
            paths = re.findall(r'\]\((tests/[^)]+)\)', cells[-1])
            assert paths, line
            assert all(Path(path).is_file() for path in paths)


def test_missing_api_has_explicit_plan_and_no_global_verified_label():
    report = inventory()
    for row in report['members']:
        assert row['status'] in ('missing', 'extension', 'present-unverified', 'verified-scoped')
        if row['status'] == 'missing':
            assert row['plan']
        if row['status'] == 'verified-scoped':
            assert row['evidence'] and all(item['scope'] for item in row['evidence'])
