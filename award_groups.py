"""Compatibility shim: implementation lives in ``oscar_predictions.award_groups``."""

from __future__ import annotations

import sys

from oscar_predictions import award_groups as _impl

sys.modules[__name__] = _impl
