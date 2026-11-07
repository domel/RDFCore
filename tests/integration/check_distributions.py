"""Reject development records and fixtures in release archives."""
from pathlib import Path, PurePosixPath
import tarfile
import zipfile

for artifact in Path('dist').iterdir():
    if artifact.suffix == '.whl':
        with zipfile.ZipFile(artifact) as archive:
            names = archive.namelist()
    elif artifact.name.endswith('.tar.gz'):
        with tarfile.open(artifact) as archive:
            names = archive.getnames()
    else:
        continue
    forbidden = {'AGENTS.md', 'spec.md', 'tests', 'benchmarks', '.w3c', '__pycache__', '.pytest_cache'}
    assert not any(forbidden.intersection(PurePosixPath(name).parts) for name in names), artifact
    assert any(PurePosixPath(name).name == 'LICENSE' for name in names), artifact
