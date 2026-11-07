"""I/O failures remain visible and preserve stream ownership."""

from io import BytesIO
import errno
import pytest
from rdfcore import io, pipeline

DATA = b'<urn:s> <urn:p> "v" .\n'


@pytest.mark.parametrize("compression", ["gz", "bz2", "xz"])
def test_owned_codec_constructor_failure_closes_raw(monkeypatch, tmp_path, compression):
    raw = BytesIO()
    monkeypatch.setattr(io.Path, "open", lambda *a, **k: raw)

    def fail(*args, **kwargs):
        raise OSError(errno.ENOSPC, "full")

    module, name = {
        "gz": (io.gzip, "GzipFile"),
        "bz2": (io.bz2, "BZ2File"),
        "xz": (io.lzma, "LZMAFile"),
    }[compression]
    monkeypatch.setattr(module, name, fail)
    with pytest.raises(OSError):
        io.open_output(tmp_path / "out", compression=compression)
    assert raw.closed


@pytest.mark.parametrize("compression", ["gz", "bz2", "xz"])
def test_owned_compressed_close_closes_raw(monkeypatch, tmp_path, compression):
    raw = BytesIO()
    monkeypatch.setattr(io.Path, "open", lambda *a, **k: raw)
    writer, owned = io.open_output(tmp_path / "out", compression=compression)
    assert owned
    writer.write(DATA)
    writer.close()
    assert raw.closed


@pytest.mark.parametrize("phase", ["write", "flush"])
def test_disk_full_and_flush_errors_keep_caller_open(phase):
    class Sink(BytesIO):
        def write(self, data):
            if phase == "write":
                raise OSError(errno.ENOSPC, "full")
            return super().write(data)

        def flush(self):
            if phase == "flush":
                raise OSError("flush failed")

    target = Sink()
    with pytest.raises(OSError):
        pipeline.convert(BytesIO(DATA), target, input_format="nt", output_format="nt")
    assert not target.closed


def test_permission_error_does_not_close_caller_input(monkeypatch, tmp_path):
    source = BytesIO(DATA)

    def denied(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(io.Path, "open", denied)
    with pytest.raises(PermissionError):
        pipeline.convert(
            source, tmp_path / "out.nt", input_format="nt", output_format="nt"
        )
    assert not source.closed


def test_owned_close_error_still_closes_raw():
    raw = BytesIO()

    class Codec:
        def close(self):
            raise OSError("close failed")

    with pytest.raises(OSError, match="close failed"):
        io._OwnedCodecStream(Codec(), raw).close()
    assert raw.closed


def test_bad_compression_does_not_truncate_output(tmp_path):
    path = tmp_path / "out"
    path.write_bytes(b"keep")
    with pytest.raises(ValueError, match="compression"):
        io.open_output(path, compression="zip")
    assert path.read_bytes() == b"keep"


@pytest.mark.parametrize("compression", ["gz", "bz2", "xz"])
def test_corrupt_compressed_input_closes_owned_file(monkeypatch, tmp_path, compression):
    raw = BytesIO(b"not compressed")
    monkeypatch.setattr(io.Path, "open", lambda *a, **k: raw)
    error = {"gz": io.gzip.BadGzipFile, "bz2": OSError, "xz": io.lzma.LZMAError}[
        compression
    ]
    with pytest.raises(error):
        pipeline.count(tmp_path / "input", "nt", input_compression=compression)
    assert raw.closed


def test_owned_input_closed_when_initial_read_fails(monkeypatch):
    class Broken(BytesIO):
        def read(self, *args):
            raise OSError("initial read failed")

    raw = Broken()
    monkeypatch.setattr(io.Path, "open", lambda *args, **kwargs: raw)
    with pytest.raises(OSError, match="initial read"):
        io.open_input("data.nt")
    assert raw.closed
