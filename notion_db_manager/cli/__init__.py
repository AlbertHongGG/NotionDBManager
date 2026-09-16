from __future__ import annotations

import sys

from notion_db_manager.cli.dispatch import Dispatcher
from notion_db_manager.cli.parser import build_parser
from notion_db_manager.core.exceptions import NDMError


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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
