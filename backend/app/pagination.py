"""Пагинация по курсору («дай записи раньше вот этой»), а не по сдвигу.

Сдвиг (offset) с каждой страницей медленнее — база перебирает все пропущенные записи —
и задваивает строки, если сверху появилась новая запись. Курсор — момент и id последней
показанной записи: следующая страница строго раньше неё, по индексу, с любой глубины.
"""

import base64
import binascii
from datetime import datetime

from fastapi import HTTPException, status

PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def encode_cursor(at: datetime, row_id: int) -> str:
    raw = f"{at.isoformat()}|{row_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    """(момент, id) или 422 — курсор пришёл от клиента и мог быть испорчен."""
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        at, row_id = base64.urlsafe_b64decode(padded).decode().split("|")
        moment = datetime.fromisoformat(at)
        if moment.tzinfo is None:
            raise ValueError("курсор без часового пояса")
        return moment, int(row_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неверный курсор") from error
