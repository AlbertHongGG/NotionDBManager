from __future__ import annotations

import argparse

from notion_db_manager.cli.handlers import (
    ActionHandler,
    EnrichHandler,
    ReaderHandler,
    WriterHandler,
)
from notion_db_manager.core.config import EnvLoader
from notion_db_manager.core.exceptions import ValidationError


class Dispatcher:
    """Dispatches parsed CLI commands to category-specific ActionHandlers."""

    def __init__(self, handlers: dict[str, ActionHandler] | None = None) -> None:
        self.handlers = handlers or {
            "reader": ReaderHandler(),
            "writer": WriterHandler(),
            "enrich": EnrichHandler(),
        }

    def dispatch(self, args: argparse.Namespace) -> None:
        EnvLoader.load()

        handler = self.handlers.get(args.category)
        if not handler:
            raise ValidationError(f"未知的指令類別: {args.category}")

        handler.handle(args)
