from __future__ import annotations

import argparse


def add_common_database_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--token", help="Notion integration token; defaults to .env or environment variables")
    parser.add_argument("--database-name", help="Notion database name; defaults to .env or environment variables")
    parser.add_argument("--database-id", help="Exact Notion database ID or URL; defaults to .env or environment variables")
    parser.add_argument("--page", help="Parent page name, Page ID, or Notion URL to scope the database; defaults to .env")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read and write Notion databases as JSON")
    subparsers = parser.add_subparsers(dest="category", required=True)

    # Reader category
    reader = subparsers.add_parser("reader", help="Reader operations")
    reader_subparsers = reader.add_subparsers(dest="action", required=True)

    # reader export-all
    export_all = reader_subparsers.add_parser("export-all", help="Export all rows and all columns")
    add_common_database_args(export_all)
    export_all.add_argument("-o", "--output", required=True, help="Output JSON file path")

    # reader export-columns
    export_columns = reader_subparsers.add_parser("export-columns", help="Export only selected columns")
    add_common_database_args(export_columns)
    export_columns.add_argument("--columns", nargs="+", required=True, help="Column names to export")
    export_columns.add_argument("-o", "--output", required=True, help="Output JSON file path")

    # reader export-rows
    export_rows = reader_subparsers.add_parser("export-rows", help="Export only selected row indexes")
    add_common_database_args(export_rows)
    export_rows.add_argument("--rows", required=True, help="Row indexes, e.g. 1,3,5-7")
    export_rows.add_argument("-o", "--output", required=True, help="Output JSON file path")

    # Writer category
    writer = subparsers.add_parser("writer", help="Writer operations")
    writer_subparsers = writer.add_subparsers(dest="action", required=True)

    # writer import-full
    import_full = writer_subparsers.add_parser("import-full", help="Import JSON created by export-all")
    add_common_database_args(import_full)
    import_full.add_argument("--input", required=True, help="Input JSON file path")
    import_full.add_argument(
        "--mode",
        choices=["append", "replace"],
        required=True,
        help="append or replace existing rows",
    )

    # writer write-columns
    write_columns = writer_subparsers.add_parser("write-columns", help="Write partial column data from JSON")
    add_common_database_args(write_columns)
    write_columns.add_argument("--input", required=True, help="Input JSON file path")
    write_columns.add_argument("--start-index", type=int, default=1, help="Target row index, starts from 1")

    # writer write-rows
    write_rows = writer_subparsers.add_parser("write-rows", help="Append, insert, or overwrite whole rows")
    add_common_database_args(write_rows)
    write_rows.add_argument("--input", required=True, help="Input JSON file path")
    write_rows.add_argument("--mode", choices=["append", "insert", "overwrite"], required=True)
    write_rows.add_argument("--index", type=int, help="Required for insert and overwrite")

    return parser
