#!/usr/bin/env python3
"""Regression test for spaces in the required occupation field."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/"index.html").read_text(encoding="utf-8")
server=(ROOT/"server/server.js").read_text(encoding="utf-8")
assert '<input id="userOccupation" name="occupation" type="text" dir="auto"' in html
assert "function isNativeControlTarget(target)" in html
assert "isNativeControlTarget(e.target)||isNativeControlTarget(document.activeElement)" in html
assert "occupation:p.occupation.normalize('NFC').trim()" in server
# Internal spaces are never collapsed or stripped by client/server occupation handling.
assert "occupation:$('userOccupation').value.trim()" in html
print("JOB_SPACE_REGRESSION_STATIC_OK")
