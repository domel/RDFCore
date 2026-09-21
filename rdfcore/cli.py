"""Minimal streaming command-line interface."""

from __future__ import annotations

import argparse
import sys

from .pipeline import convert, count, validate


def build_parser():
    parser = argparse.ArgumentParser(prog="rdfcore")
    commands = parser.add_subparsers(dest="command", required=True)

    conversion = commands.add_parser("convert")
    conversion.add_argument("input", nargs="?", default="-")
    conversion.add_argument("output", nargs="?", default="-")
    conversion.add_argument("--from", dest="input_format", required=True)
    conversion.add_argument("--to", dest="output_format", required=True)
    conversion.add_argument("--dataset-policy", default="strict", choices=("strict", "default", "union"))

    for name in ("count", "validate"):
        command = commands.add_parser(name)
        command.add_argument("input", nargs="?", default="-")
        command.add_argument("--format", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "convert":
        convert(
            args.input,
            args.output,
            input_format=args.input_format,
            output_format=args.output_format,
            dataset_policy=args.dataset_policy,
        )
        return 0
    if args.command == "count":
        print(count(args.input, args.format))
        return 0
    try:
        validate(args.input, args.format)
    except Exception as error:
        print(f"invalid RDF: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
