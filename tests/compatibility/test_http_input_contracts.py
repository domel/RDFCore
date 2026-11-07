"""HTTP observations against RDFLib 7.6.0, using only a local server."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
import rdflib
import rdfcore


@contextmanager
def server(content_type="text/turtle", body=b"<s> <p> <o> ."):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.path, self.headers.get("Accept")))
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/final/data")
                self.end_headers()
                return
            self.send_response(200)
            if content_type is not None:
                self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join()


def test_bare_content_type_selects_parser_without_explicit_format():
    with server("application/n-triples", b'<urn:s> <urn:p> "v" .') as (url, _):
        results = []
        for module in (rdflib, rdfcore):
            graph = module.Graph().parse(url + "/misleading.xml")
            results.append({tuple(map(str, triple)) for triple in graph})
        assert results[0] == results[1] == {("urn:s", "urn:p", "v")}


@pytest.mark.parametrize("explicit", [False, True])
def test_versioned_http_header_and_explicit_format_precedence(explicit):
    from rdfcore import TripleTerm

    data = b"<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> ."
    with server("application/n-triples; version=1.2", data) as (url, requests):
        if explicit:
            with pytest.raises(rdfcore.ParserError):
                rdfcore.Graph().parse(url + "/data", format="nt")
        else:
            graph = rdfcore.Graph().parse(url + "/misleading.xml")
            assert isinstance(next(iter(graph))[2], TripleTerm)


def test_explicit_rdf12_format_announces_requested_media_version():
    with server("application/n-triples; version=1.2", b'<urn:s> <urn:p> "v" .') as (
        url,
        requests,
    ):
        rdfcore.Graph().parse(url + "/data", format="nt12")
        assert requests[0][1] == "application/n-triples; version=1.2"
