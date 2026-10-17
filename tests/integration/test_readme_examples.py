"""Execute the documented Python examples against small local fixtures."""

import gzip
from pathlib import Path
import re


def test_readme_python_examples(tmp_path, monkeypatch):
    readme = (Path(__file__).resolve().parents[2] / 'README.md').read_text(encoding='utf-8')
    triple = '<urn:s> <urn:keep> "value" .\n'
    for name in ('input.nt', 'large.nt'):
        (tmp_path / name).write_text(triple, encoding='utf-8')
    (tmp_path / 'input.nq').write_text(triple + '<urn:s> <urn:p> "named" <urn:g> .\n', encoding='utf-8')
    (tmp_path / 'input.ttl').write_text(triple, encoding='utf-8')
    (tmp_path / 'large.nt.gz').write_bytes(gzip.compress(triple.encode('utf-8')))
    monkeypatch.chdir(tmp_path)
    namespace = {'__name__': '__readme_examples__'}
    blocks = re.findall(r'```python\n(.*?)```', readme, re.S)
    assert blocks
    for index, block in enumerate(blocks):
        exec(compile(block, f'README.md example {index + 1}', 'exec'), namespace)
