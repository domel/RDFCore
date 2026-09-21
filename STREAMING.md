# Streaming and memory behavior

`parse_stream()` and `pipeline.convert()` are streamable for N-Triples and
N-Quads. Turtle and TriG parsers are incremental and can consume bounded
readers; their streaming serializers are available with `mode="stream"`.

`external_sort()` is an external-memory operation for triples and quads. It
uses fixed-size in-memory runs and temporary files, then performs a k-way
merge. `max_open_runs` bounds the merge fan-in and triggers additional merge
passes when necessary. `SQLiteStore` is disk-backed and does not materialize
all statements in Python memory.

The normal `Graph`/`Dataset` containers, pretty serializers, isomorphism and
canonicalization operations are materializing operations. They may retain or
sort the complete graph.

Use `benchmark_parse()` to collect input size, statement count, elapsed time,
MB/s, statements/s and peak RSS for a streaming parse.
