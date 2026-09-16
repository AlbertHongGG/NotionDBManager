from __future__ import annotations

import argparse

from notion_db_manager.application.commands import (
    BaseCommand,
    CommandResult,
    ExportAllCommand,
    ExportColumnsCommand,
    ExportRowsCommand,
    ImportFullCommand,
    WriteColumnsCommand,
    WriteRowsCommand,
)
from notion_db_manager.cli.prompt import resolve_settings
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.infrastructure.notion import NotionGatewayImpl, NotionHttpClient
from notion_db_manager.infrastructure.storage import JsonDocumentStorage, PathResolver


class Dispatcher:
    """Dispatches parsed CLI commands to domain-level Application Commands."""

    def dispatch(self, args: argparse.Namespace) -> None:
        settings = resolve_settings(args)

        client = NotionHttpClient(token=settings.token)
        gateway = NotionGatewayImpl(client=client)
        storage = JsonDocumentStorage(path_resolver=PathResolver())

        database = gateway.search_database_by_name(settings.database_name)
        database = gateway.ensure_order_property(database)

        cmd: BaseCommand
        result: CommandResult

        category = args.category
        action = args.action

        if category == "reader":
            if action == "export-all":
                cmd = ExportAllCommand(gateway, storage)
                result = cmd.execute(database, output_path=args.output)
            elif action == "export-columns":
                cmd = ExportColumnsCommand(gateway, storage)
                result = cmd.execute(database, output_path=args.output, columns=args.columns)
            elif action == "export-rows":
                cmd = ExportRowsCommand(gateway, storage)
                result = cmd.execute(database, output_path=args.output, row_expression=args.rows)
            else:
                raise ValidationError(f"未知的 reader 動作: {action}")

        elif category == "writer":
            if action == "import-full":
                cmd = ImportFullCommand(gateway, storage)
                result = cmd.execute(database, input_path=args.input, mode=args.mode)
            elif action == "write-columns":
                cmd = WriteColumnsCommand(gateway, storage)
                result = cmd.execute(database, input_path=args.input, start_index=args.start_index)
            elif action == "write-rows":
                cmd = WriteRowsCommand(gateway, storage)
                result = cmd.execute(
                    database,
                    input_path=args.input,
                    mode=args.mode,
                    index=args.index,
                )
            else:
                raise ValidationError(f"未知的 writer 動作: {action}")
        else:
            raise ValidationError(f"未知的指令類別: {category}")

        print(result.message)
