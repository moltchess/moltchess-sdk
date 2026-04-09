from __future__ import annotations

import json
import re
from typing import Any, Mapping


def extract_json_object(text: str) -> Mapping[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if fence:
        return json.loads(fence.group(1))
    return json.loads(text)


def parse_move_choice(data: Mapping[str, Any]) -> tuple[str | None, str | None]:
    san = data.get("move_san")
    uci = data.get("move_uci")
    if isinstance(san, str):
        san = san.strip() or None
    else:
        san = None
    if isinstance(uci, str):
        uci = uci.strip().lower() or None
    else:
        uci = None
    return san, uci
