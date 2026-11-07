"""Run directly outside the checkout after installing a distribution."""
from importlib.metadata import metadata, version
from pathlib import Path
import subprocess
import sys
import tempfile

import rdfcore

assert version('rdfcore') == rdfcore.__version__
assert metadata('rdfcore')['License-Expression'] == 'MIT'
assert not Path(rdfcore.__file__).resolve().is_relative_to(Path(__file__).resolve().parents[2] / 'rdfcore')
graph = rdfcore.Graph()
graph.add((rdfcore.URIRef('urn:s'), rdfcore.URIRef('urn:p'), rdfcore.Literal('value')))
for fmt in ('nt', 'turtle', 'xml', 'nt12', 'turtle12', 'xml12'):
    assert len(rdfcore.Graph().parse(data=graph.serialize(format=fmt), format=fmt)) == 1
with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / 'input.nt'
    source.write_text(graph.serialize(format='nt'), encoding='utf-8')
    output = subprocess.check_output([sys.executable, '-m', 'rdfcore.cli', 'count', str(source), '--format', 'nt'], text=True)
    assert output.strip() == '1'
    subprocess.run([sys.executable, '-m', 'rdfcore.cli', 'validate', str(source), '--format', 'nt'], check=True)
subprocess.run(['rdfcore', '--help'], check=True, stdout=subprocess.DEVNULL)
