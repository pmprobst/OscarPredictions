"""Compatibility shim: implementation lives in ``oscar_predictions.oscar_scrape``."""

from __future__ import annotations

import sys

from oscar_predictions import oscar_scrape as _impl

sys.modules[__name__] = _impl
