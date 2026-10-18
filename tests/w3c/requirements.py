"""Offline source inventory and evidence checks, not a conformance oracle.

The inventory deliberately includes prose without RFC 2119 keywords. A human
must still review exclusions and map clauses to normative requirements.
"""

from hashlib import sha256
from html.parser import HTMLParser


class _Inventory(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.blocks = []
        self.clauses = []
        self.exclusions = []

    def handle_starttag(self, tag, attrs):
        # HTML permits omitted end tags; HTMLParser does not insert them.
        if tag in {'p', 'div', 'section', 'ul', 'ol', 'dl', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self._close_optional({'p'}, {'section', 'div', 'li', 'td', 'body', 'html'})
        if tag == 'li':
            self._close_optional({'li'}, {'ul', 'ol'})
        if tag in {'dt', 'dd'}:
            self._close_optional({'dt', 'dd'}, {'dl'})
        if tag == 'tr':
            self._close_optional({'tr'}, {'table'})
        attrs = dict(attrs)
        anchor = attrs.get('id', self.stack[-1][1] if self.stack else '')
        excluded = self.stack[-1][2] if self.stack else False
        reason = None
        if tag in {'script', 'style', 'nav'}:
            reason = tag
        elif {'informative', 'example'} & set(attrs.get('class', '').split()):
            reason = 'informative or example'
        elif attrs.get('id', '') in {'references', 'abstract', 'sotd', 'toc', 'acknowledgements'}:
            reason = attrs['id']
        if reason:
            self.exclusions.append({'anchor': anchor, 'reason': reason})
        self.stack.append((tag, anchor, excluded or bool(reason)))
        if not self.stack[-1][2] and tag in {'p', 'li', 'dt', 'dd', 'tr', 'pre'}:
            self.blocks.append({'tag': tag, 'anchor': anchor, 'depth': len(self.stack), 'text': [], 'td': False})
        if tag == 'td':
            for block in self.blocks:
                if block['tag'] == 'tr':
                    block['td'] = True
        if tag in {'br', 'hr', 'img', 'input', 'meta', 'link', 'wbr', 'source', 'area', 'base', 'embed', 'param', 'col'}:
            self.handle_endtag(tag)

    def _close_optional(self, tags, boundaries):
        for tag, _, _ in reversed(self.stack):
            if tag in boundaries:
                break
            if tag in tags:
                self.handle_endtag(tag)
                break

    def close(self):
        super().close()
        while self.stack:
            self.handle_endtag(self.stack[-1][0])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1][0] == tag:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.stack and not self.stack[-1][2]:
            for block in self.blocks:
                block['text'].append(data)

    def handle_endtag(self, tag):
        indexes = [i for i, item in enumerate(self.stack) if item[0] == tag]
        if not indexes:
            return
        depth = indexes[-1] + 1
        closing = [b for b in self.blocks if b['depth'] >= depth]
        for block in closing:
            text = ' '.join(' '.join(block['text']).split())
            if text and (block['tag'] != 'tr' or block['td']):
                kind = ('grammar' if '::=' in text else 'condition') if block['tag'] in {'tr', 'pre'} else (
                    'list-item' if block['tag'] == 'li' else 'prose')
                self.clauses.append({'anchor': block['anchor'], 'kind': kind, 'text': text})
            self.blocks.remove(block)
        del self.stack[depth - 1:]


def inventory_document(name, source, url, date, informative=False):
    """Inventory local UTF-8 HTML; never fetch a mutable remote document."""
    report = {'document': name, 'url': url, 'date': date,
              'source_sha256': sha256(source).hexdigest(), 'clauses': [], 'exclusions': []}
    if informative:
        report['exclusion_reason'] = 'Informative document; no independent normative requirements.'
        return report
    parser = _Inventory()
    parser.feed(source.decode('utf-8-sig'))
    parser.close()
    seen = set()
    for clause in parser.clauses:
        fingerprint = sha256((clause['anchor'] + '\n' + clause['kind'] + '\n' + clause['text']).encode()).hexdigest()
        identifier = name + ':' + fingerprint
        if identifier not in seen:
            report['clauses'].append({'id': identifier, **clause})
            seen.add(identifier)
    report['exclusions'] = parser.exclusions
    return report


def validate_matrix(reports, records, *, require_provenance=False):
    """Reject accounting gaps; a passing result does not prove conformance."""
    expected, documents = {}, set()
    for report in reports:
        if report['document'] in documents:
            raise ValueError('duplicate source document: ' + report['document'])
        documents.add(report['document'])
        for clause in report['clauses']:
            if clause['id'] in expected:
                raise ValueError('duplicate source clause: ' + clause['id'])
            expected[clause['id']] = (report, clause)
    seen = set()
    statuses = {'implemented', 'partial', 'missing', 'not-applicable-with-reason'}
    for record in records:
        identifier = record['id']
        if identifier in seen:
            raise ValueError('duplicate requirement: ' + identifier)
        if identifier not in expected:
            raise ValueError('unknown requirement: ' + identifier)
        seen.add(identifier)
        if require_provenance:
            source, clause = expected[identifier]
            if record.get('reviewed') is not True:
                raise ValueError('manual review required: ' + identifier)
            for field in ('document', 'url', 'date', 'source_sha256'):
                if record.get(field) != source[field]:
                    raise ValueError('source provenance mismatch for ' + field + ': ' + identifier)
            if record.get('anchor') != clause['anchor']:
                raise ValueError('anchor provenance mismatch: ' + identifier)
        if record.get('status') not in statuses:
            raise ValueError('invalid requirement status: ' + identifier)
        for field in ('implementation', 'expected', 'reason'):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError('missing ' + field + ': ' + identifier)
        if not isinstance(record.get('tests'), list) or any(
                not isinstance(test, str) or not test.strip() for test in record['tests']):
            raise ValueError('tests must be a list: ' + identifier)
        if record['status'] == 'implemented' and not record['tests']:
            raise ValueError('implemented requires test evidence: ' + identifier)
    missing = sorted(expected.keys() - seen)
    if missing:
        raise ValueError('unaccounted requirements: ' + ', '.join(missing))
    return {'requirements': len(expected), 'unaccounted': []}


def main(argv=None):
    """Read an explicit local manifest; emit JSON without touching spec.md."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path, help='JSON list of local source records')
    parser.add_argument('--matrix', type=Path, help='JSON requirement records to validate')
    parser.add_argument('--strict', action='store_true',
                        help='require reviewed records bound to document revision, hash and anchor')
    args = parser.parse_args(argv)
    if args.strict and args.matrix is None:
        parser.error('--strict requires --matrix')
    sources = json.loads(args.manifest.read_text(encoding='utf-8'))
    reports = []
    names = set()
    for source in sources:
        name = source['document']
        if name in names:
            parser.error('duplicate source document: ' + name)
        names.add(name)
        path = args.manifest.parent / source['path']
        data = path.read_bytes()
        if source.get('source_sha256') is not None and sha256(data).hexdigest() != source['source_sha256']:
            parser.error('source hash mismatch: ' + name)
        reports.append(inventory_document(name, data, source['url'], source['date'],
                                          informative=source.get('informative', False)))
    result = {'documents': reports, 'scope': 'candidate clauses; manual normative review required'}
    if args.matrix:
        result['accounting'] = validate_matrix(reports, json.loads(args.matrix.read_text(encoding='utf-8')),
                                               require_provenance=args.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
