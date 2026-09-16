from __future__ import annotations

import pytest

from notion_db_manager.core.exceptions import ValidationError
from notion_db_manager.domain.validation import parse_row_indices


def test_parse_row_indices_success() -> None:
    assert parse_row_indices("1") == [1]
    assert parse_row_indices("1, 3, 5") == [1, 3, 5]
    assert parse_row_indices("1,3,5-7") == [1, 3, 5, 6, 7]
    assert parse_row_indices("5-7, 2") == [2, 5, 6, 7]
    assert parse_row_indices("1-3, 2-4") == [1, 2, 3, 4]


def test_parse_row_indices_errors() -> None:
    with pytest.raises(ValidationError):
        parse_row_indices("")

    with pytest.raises(ValidationError):
        parse_row_indices("0")

    with pytest.raises(ValidationError):
        parse_row_indices("5-2")

    with pytest.raises(ValidationError):
        parse_row_indices("abc")
