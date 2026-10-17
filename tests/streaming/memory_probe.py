"""Fresh-process RSS probe used only by streaming regression tests."""

import argparse
import json
import platform
import resource
import sys

from rdfcore.streaming import parse_stream


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('format')
    parser.add_argument('--collect', action='store_true')
    args = parser.parse_args()
    class Counter:
        count = 0
        def add(self, statement):
            self.count += 1
    sink = Counter()
    if args.collect:
        records = list(parse_stream(args.path, args.format))
        count = len(records)
    else:
        parse_stream(args.path, args.format, sink)
        count = sink.count
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({'statements': count, 'peak_rss_bytes': peak if sys.platform == 'darwin' else peak * 1024,
                      'python': platform.python_version(), 'platform': sys.platform, 'unit': 'bytes'}))


if __name__ == '__main__':
    main()
