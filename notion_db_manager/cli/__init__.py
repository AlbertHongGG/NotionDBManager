from __future__ import annotations

import sys

from notion_db_manager.cli.dispatch import Dispatcher
from notion_db_manager.cli.parser import build_parser
from notion_db_manager.core.exceptions import NDMError


def main() -> None:
    dispatcher = Dispatcher()
    parser = build_parser()
    args = parser.parse_args()

    try:
        dispatcher.dispatch(args)
    except NDMError as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        print("\n操作已取消。", file=sys.stderr)
        raise SystemExit(130)


__all__ = ["Dispatcher", "build_parser", "main"]
