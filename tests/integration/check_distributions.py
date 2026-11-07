"""Validate release archives and emit their source/dependency provenance."""
from email.parser import Parser
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import tarfile
import zipfile

artifacts = []
for artifact in sorted(Path('dist').iterdir()):
    if artifact.suffix == '.whl':
        kind = 'wheel'
        with zipfile.ZipFile(artifact) as archive:
            names = archive.namelist()
            metadata_path = next(name for name in names if name.endswith('.dist-info/METADATA'))
            metadata = Parser().parsestr(archive.read(metadata_path).decode('utf-8'))
    elif artifact.name.endswith('.tar.gz'):
        kind = 'sdist'
        with tarfile.open(artifact) as archive:
            names = archive.getnames()
            metadata_path = next(name for name in names
                                 if len(PurePosixPath(name).parts) == 2 and name.endswith('/PKG-INFO'))
            with archive.extractfile(metadata_path) as stream:
                metadata = Parser().parsestr(stream.read().decode('utf-8'))
    else:
        continue
    forbidden = {'AGENTS.md', 'spec.md', 'tests', 'benchmarks', '.w3c', '__pycache__', '.pytest_cache'}
    assert not any(forbidden.intersection(PurePosixPath(name).parts) for name in names), artifact
    assert any(PurePosixPath(name).name == 'LICENSE' for name in names), artifact
    assert metadata['Name'] == 'rdfcore' and metadata['License-Expression'] == 'MIT', artifact
    artifacts.append({'name': artifact.name, 'kind': kind,
                      'version': metadata['Version'], 'license': metadata['License-Expression'],
                      'dependencies': metadata.get_all('Requires-Dist', []),
                      'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()})
assert {item['kind'] for item in artifacts} == {'wheel', 'sdist'}, 'Both wheel and sdist are required'
assert len({item['version'] for item in artifacts}) == 1, 'Distribution versions differ'
source_clean = not subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()
assert source_clean, 'Release provenance requires a clean source checkout'
print(json.dumps({'source_clean': source_clean, 'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  'python': platform.python_version(), 'artifacts': artifacts}, indent=2))
