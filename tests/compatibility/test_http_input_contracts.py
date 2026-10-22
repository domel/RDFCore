"""HTTP observations against RDFLib 7.6.0, using only a local server."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
import rdflib
import rdfcore


@contextmanager
def server(content_type='text/turtle', body=b'<s> <p> <o> .'):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.path, self.headers.get('Accept')))
            if self.path == '/redirect':
                self.send_response(302)
                self.send_header('Location', '/final/data')
                self.end_headers()
                return
            self.send_response(200)
            if content_type is not None:
                self.send_header('Content-Type', content_type)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield f'http://127.0.0.1:{httpd.server_port}', requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join()


@pytest.mark.parametrize('format', ['turtle', 'ttl', 'xml', 'nt', 'trig'])
def test_explicit_accept_matches_reference(format):
    body = b'<urn:s> <urn:p> <urn:o> .'
    if format == 'xml':
        body = b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
    with server(body=body) as (url, requests):
        for module in (rdflib, rdfcore):
            cls = module.Dataset if format == 'trig' else module.Graph
            cls().parse(url+'/data', format=format)
        assert requests[0][1] == requests[1][1]


@pytest.mark.parametrize('public_id', [None, '', 'https://override.example/base/'])
def test_redirect_base_and_explicit_public_id_match_reference(public_id):
    with server() as (url, requests):
        results = []
        for module in (rdflib, rdfcore):
            graph = module.Graph().parse(url+'/redirect', format='turtle', publicID=public_id)
            results.append({tuple(map(str, triple)) for triple in graph})
        assert results[0] == results[1]
        base = public_id or (url+'/' if public_id == '' else url+'/final/')
        assert results[1] == {(base+'s', base+'p', base+'o')}


def test_bare_content_type_selects_parser_without_explicit_format():
    with server('application/n-triples', b'<urn:s> <urn:p> "v" .') as (url, _):
        results = []
        for module in (rdflib, rdfcore):
            graph = module.Graph().parse(url+'/misleading.xml')
            results.append({tuple(map(str, triple)) for triple in graph})
        assert results[0] == results[1] == {('urn:s', 'urn:p', 'v')}


@pytest.mark.parametrize('explicit', [False, True])
def test_versioned_http_header_and_explicit_format_precedence(explicit):
    from rdfcore import TripleTerm
    data = b'<urn:s> <urn:p> <<( <urn:a> <urn:b> <urn:c> )>> .'
    with server('application/n-triples; version=1.2', data) as (url, requests):
        if explicit:
            with pytest.raises(rdfcore.ParserError):
                rdfcore.Graph().parse(url+'/data', format='nt')
        else:
            graph = rdfcore.Graph().parse(url+'/misleading.xml')
            assert isinstance(next(iter(graph))[2], TripleTerm)


def test_explicit_rdf12_format_announces_requested_media_version():
    with server('application/n-triples; version=1.2', b'<urn:s> <urn:p> "v" .') as (url, requests):
        rdfcore.Graph().parse(url+'/data', format='nt12')
        assert requests[0][1] == 'application/n-triples; version=1.2'


@pytest.mark.parametrize('explicit', [False, True])
def test_malformed_version_header_is_ignored_only_with_explicit_format(explicit):
    with server('text/turtle; version=unknown') as (url, _):
        if explicit:
            assert len(rdfcore.Graph().parse(url+'/data', format='turtle')) == 1
        else:
            with pytest.raises(ValueError, match='unsupported media version'):
                rdfcore.Graph().parse(url+'/data')


def test_response_is_closed_on_success_and_parser_failure(monkeypatch):
    from io import BytesIO
    from rdfcore import parser
    for data in (b'<urn:s> <urn:p> "v" .', b'not RDF'):
        response = BytesIO(data)
        response.headers = {'Content-Type': 'text/turtle'}
        response.geturl = lambda: 'https://final.example/base/data'
        monkeypatch.setattr(parser, 'urlopen', lambda *args, **kwargs: response)
        try:
            rdfcore.Graph().parse('https://initial.example/data')
        except rdfcore.BadSyntax:
            assert data == b'not RDF'
        assert response.closed


def test_accept_extension_is_explicit_and_rejects_header_injection():
    with server() as (url, requests):
        rdfcore.Graph().parse(url+'/data', format='turtle', http_accept='text/turtle; version=1.2-basic')
        assert requests[0][1] == 'text/turtle; version=1.2-basic'
        with pytest.raises(ValueError, match='HTTP header'):
            rdfcore.Graph().parse(url+'/data', http_accept='text/turtle\r\nX: y')
        assert len(requests) == 1


def test_custom_bare_mime_with_charset_matches_reference(monkeypatch):
    from rdflib import plugin as reference_plugin
    from rdflib.parser import Parser as ReferenceParser
    from rdfcore import plugin
    from rdfcore.parser import Parser
    from rdfcore.plugins.parsers.rdfxml import RDFXMLParser
    name = 'application/x-review-xml'
    monkeypatch.setitem(plugin._registry, (name, Parser), plugin.Plugin(name, Parser, implementation=RDFXMLParser))
    monkeypatch.setitem(reference_plugin._plugins, (name, ReferenceParser),
        reference_plugin.Plugin(name, ReferenceParser, 'rdflib.plugins.parsers.rdfxml', 'RDFXMLParser'))
    body = b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
    with server(name+'; charset=utf-8', body) as (url, _):
        for module in (rdflib, rdfcore):
            graph = module.Graph()
            assert graph.parse(url+'/misleading.ttl') is graph
            assert len(graph) == 0


def test_exact_parameterized_custom_http_mime_wins_without_a_bare_plugin(monkeypatch):
    from rdfcore import plugin
    from rdfcore.parser import Parser
    from rdfcore.plugins.parsers.rdfxml import RDFXMLParser
    name = 'application/x-review-only; profile=custom'
    monkeypatch.setitem(plugin._registry, (name, Parser), plugin.Plugin(name, Parser, implementation=RDFXMLParser))
    body = b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
    with server(name, body) as (url, _):
        assert len(rdfcore.Graph().parse(url+'/misleading.ttl')) == 0
