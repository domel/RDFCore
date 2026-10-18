"""Compare accounted W3C executions without normalizing away failures."""

from collections import Counter

STATUSES = ('passed', 'failed', 'unsupported', 'error')


def _executions(report):
    executions, suite_errors, seen_suites = {}, [], set()
    if not report['suites']:
        raise ValueError('report has no suite accounting')
    for suite in report['suites']:
        scope = (suite['category'], suite['rdf_version'], suite['format'])
        if scope in seen_suites:
            raise ValueError('duplicate suite accounting')
        seen_suites.add(scope)
        counts = Counter(test['status'] for test in suite['tests'])
        expected = {status: counts[status] for status in STATUSES}
        if (set(counts) - set(STATUSES) or suite['counts'] != expected
                or any(type(count) is not int or count < 0 for count in suite['counts'].values())
                or type(suite['total']) is not int or suite['total'] != len(suite['tests'])):
            raise ValueError('inconsistent execution accounting')
        if not suite['tests'] and not suite.get('suite_error'):
            raise ValueError('empty suite accounting without a suite error')
        if suite.get('suite_error'):
            suite_errors.append({'scope': scope, 'reason': suite['suite_error']})
        repeated = Counter()
        for test in suite['tests']:
            identity = (*scope, test['id'], test.get('manifest', ''))
            occurrence = repeated[identity]
            repeated[identity] += 1
            executions[(*identity, occurrence)] = test
    totals = Counter(test['status'] for test in executions.values())
    if 'totals' in report and report['totals'] != {status: totals[status] for status in STATUSES}:
        raise ValueError('inconsistent global status accounting')
    for field, actual in (('test_executions', len(executions)),
                          ('unique_test_ids', len({test['id'] for test in executions.values()}))):
        if field in report and (type(report[field]) is not int or report[field] != actual):
            raise ValueError('inconsistent global execution accounting')
    return executions, suite_errors


def compare_reports(before, after):
    """Preserve version, format, physical manifest and repeated occurrences."""
    if (before.get('execution_profile', 'default') != after.get('execution_profile', 'default')
            or before.get('parser_options', {}) != after.get('parser_options', {})):
        raise ValueError('cannot compare different execution profiles')
    previous, old_errors = _executions(before)
    current, new_errors = _executions(after)
    result = {'before_snapshot': before['snapshot'], 'after_snapshot': after['snapshot'],
              'execution_profile': after.get('execution_profile', 'default'),
              'unchanged': 0, 'changed': [], 'added': [], 'removed': [],
              'suite_errors': {'before': old_errors, 'after': new_errors}}
    for key in sorted(previous.keys() | current.keys(), key=repr):
        old, new = previous.get(key), current.get(key)
        record = {'execution': key, 'before': old, 'after': new}
        if old is None:
            result['added'].append(record)
        elif new is None:
            result['removed'].append(record)
        elif any(old.get(field) != new.get(field) for field in
                 ('status', 'reason', 'action_sha256', 'result_sha256')):
            result['changed'].append(record)
        else:
            result['unchanged'] += 1
    return result


def audit_report(report):
    """Attach reviewed explanations; neither change nor excuse test status."""
    executions, errors = _executions(report)
    from tests.w3c.known_issues import classify_issue
    issues = []
    for suite in report['suites']:
        for test in suite['tests']:
            if test['status'] != 'passed':
                issues.append({'rdf_version': suite['rdf_version'], 'format': suite['format'],
                               'id': test['id'], 'status': test['status'],
                               'observed_reason': test['reason'],
                               **classify_issue(report, suite, test)})
    return {'snapshot': report['snapshot'], 'execution_profile': report.get('execution_profile', 'default'),
            'test_executions': len(executions), 'suite_errors': errors, 'issues': issues,
            'unreviewed': sum(issue['classification'] == 'unreviewed' for issue in issues)}


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', required=True, type=Path)
    parser.add_argument('--before', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    after = json.loads(args.current.read_text(encoding='utf-8'))
    result = {'audit': audit_report(after)}
    if args.before:
        result['comparison'] = compare_reports(json.loads(args.before.read_text(encoding='utf-8')), after)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    else:
        print(rendered, end='')
    return int(bool(result['audit']['issues'] or result['audit']['suite_errors']
                    or result.get('comparison', {}).get('removed')))


if __name__ == '__main__':
    raise SystemExit(main())
