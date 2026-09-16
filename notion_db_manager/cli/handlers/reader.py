from __future__ import annotations

import argparse

from notion_db_manager.application.commands import (
    CommandResult,
    ExportAllCommand,
    ExportColumnsCommand,
    ExportRowsCommand,
)
from notion_db_manager.cli.handlers.base import ActionHandler
from notion_db_manager.cli.prompt import resolve_settings
from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.models import DatabaseQuery, PageReference
from notion_db_manager.infrastructure.notion import NotionGatewayImpl, NotionHttpClient
from notion_db_manager.infrastructure.storage import JsonDocumentStorage, PathResolver


class ReaderHandler(ActionHandler):
    """Handles all 'reader' CLI subcommands."""

    def handle(self, args: argparse.Namespace) -> None:
        settings = resolve_settings(args)

        client = NotionHttpClient(token=settings.token)
        gateway = NotionGatewayImpl(client=client)
        storage = JsonDocumentStorage(path_resolver=PathResolver())

        parent_ref = PageReference.from_raw(settings.page) if settings.page else None
        query = DatabaseQuery(
            database_name=settings.database_name,
            database_id=settings.database_id,
            parent_page=parent_ref,
        )
        database = gateway.locate_database(query)
        database = gateway.ensure_order_property(database)

        action = args.action
        result: CommandResult

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

        print(result.message)
