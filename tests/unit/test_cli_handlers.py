from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch
import pytest

from notion_db_manager.cli.dispatch import Dispatcher
from notion_db_manager.cli.handlers import ActionHandler, ReaderHandler, TravelHandler, WriterHandler
from notion_db_manager.core.exceptions import ValidationError


def test_dispatcher_routes_to_handler() -> None:
    mock_reader = MagicMock(spec=ActionHandler)
    dispatcher = Dispatcher(handlers={"reader": mock_reader})

    args = argparse.Namespace(category="reader", action="export-all")
    dispatcher.dispatch(args)

    mock_reader.handle.assert_called_once_with(args)


def test_dispatcher_unknown_category() -> None:
    dispatcher = Dispatcher(handlers={})
    args = argparse.Namespace(category="unknown_cat")

    with pytest.raises(ValidationError) as exc_info:
        dispatcher.dispatch(args)
    assert "未知的指令類別" in str(exc_info.value)


def test_reader_handler_invalid_action() -> None:
    handler = ReaderHandler()
    args = argparse.Namespace(
        token="token",
        database_name="db",
        database_id=None,
        page=None,
        action="invalid_action",
    )

    with patch("notion_db_manager.cli.handlers.reader.NotionHttpClient"), patch(
        "notion_db_manager.cli.handlers.reader.NotionGatewayImpl"
    ):
        with pytest.raises(ValidationError) as exc_info:
            handler.handle(args)
        assert "未知的 reader 動作" in str(exc_info.value)


def test_writer_handler_invalid_action() -> None:
    handler = WriterHandler()
    args = argparse.Namespace(
        token="token",
        database_name="db",
        database_id=None,
        page=None,
        action="invalid_action",
    )

    with patch("notion_db_manager.cli.handlers.writer.NotionHttpClient"), patch(
        "notion_db_manager.cli.handlers.writer.NotionGatewayImpl"
    ):
        with pytest.raises(ValidationError) as exc_info:
            handler.handle(args)
        assert "未知的 writer 動作" in str(exc_info.value)


def test_travel_handler_invalid_action() -> None:
    handler = TravelHandler()
    args = argparse.Namespace(action="invalid_action")

    with pytest.raises(ValidationError) as exc_info:
        handler.handle(args)
    assert "未知的 travel 動作" in str(exc_info.value)


def test_cli_parser_enrich_photos_missing_only() -> None:
    from notion_db_manager.cli.parser import build_parser

    parser = build_parser()

    # 1. Default when not specified -> None (so config resolver falls back to env or False)
    args_default = parser.parse_args(["travel", "enrich-photos"])
    assert args_default.missing_only is None

    # 2. When passed on CLI -> True
    args_flag = parser.parse_args(["travel", "enrich-photos", "--missing-only"])
    assert args_flag.missing_only is True

    # 3. Verify --no-missing-only does NOT exist and fails cleanly
    with pytest.raises(SystemExit):
        parser.parse_args(["travel", "enrich-photos", "--no-missing-only"])


