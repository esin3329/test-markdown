"""Python CLI for ingestion, deterministic wiki compilation, search, and checking."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .check import check, render


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="link-doctor-py", description="Ingest, compile, search, and check local Markdown knowledge bases.")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("ingest", help="convert local PDF/DOCX files to Markdown")
    ingest.add_argument("source_dir")
    ingest.add_argument("--output", required=True)
    ingest.add_argument("--recursive", action="store_true")
    compile_cmd = commands.add_parser("compile", help="compile Markdown wiki graph and diagnostics")
    compile_cmd.add_argument("root")
    compile_cmd.add_argument("--output")
    compile_cmd.add_argument("--format", choices=("text", "json", "html"), default="text")
    check_cmd = commands.add_parser("check", help="check Markdown and wiki links")
    check_cmd.add_argument("root")
    check_cmd.add_argument("--format", choices=("text", "json", "html"), default="text")
    check_cmd.add_argument("--output")
    search_cmd = commands.add_parser("search", help="semantic search with EmbeddingGemma2")
    search_cmd.add_argument("root")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--top-k", type=int, default=5)
    search_cmd.add_argument("--index-dir")
    search_cmd.add_argument("--dimension", type=int, choices=(128, 256, 512, 768), default=256)
    search_cmd.add_argument("--device")
    search_cmd.add_argument("--no-relations", action="store_true", help="skip pairwise relation candidates")
    return parser
def _assert_safe_report_output(root_path: str, output_path: str) -> None:
    root = Path(root_path).resolve(strict=True)
    target = Path(output_path).resolve()
    if target.is_relative_to(root) and target.suffix.casefold() == ".md":
        raise ValueError("Refusing to overwrite a Markdown input file")




def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "ingest":
            from .ingest import ingest
            result = ingest(args.source_dir, args.output, args.recursive)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "check":
            report = check(args.root)
        elif args.command == "compile":
            from .compile import compile_wiki
            result = compile_wiki(args.root, args.output)
            report = result["diagnostics"]
            if args.output:
                print(f"Compiled {result['entities']} pages into {args.output}; graph: {Path(args.output) / 'graph.json'}", file=sys.stderr)
        else:
            from .search import search
            result = search(args.root, args.query, args.top_k, args.index_dir, args.dimension, args.device, not args.no_relations)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "check" and args.output:
            if args.format != "html":
                raise ValueError("--output is supported only with --format html")
            _assert_safe_report_output(args.root, args.output)
            Path(args.output).write_text(render(report, args.format), encoding="utf-8")
        else:
            sys.stdout.write(render(report, args.format))
        return 1 if report["counts"]["missing"] else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"link-doctor-py: {exc}", file=sys.stderr)
        return 2
