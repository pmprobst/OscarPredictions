"""Shared argparse helpers for sync and stage CLIs."""

from __future__ import annotations

import argparse


def add_browser_args(parser: argparse.ArgumentParser) -> None:
    """Standard browser visibility flags used across all commands."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window.",
    )
    group.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible Chromium window.",
    )


def resolve_headless(args: argparse.Namespace, *, default_headless: bool = True) -> bool:
    """Resolve browser mode from --headless/--headed flags."""
    if getattr(args, "headless", False):
        return True
    if getattr(args, "headed", False):
        return False
    return default_headless


# Backward-compatible helper names used by existing stage modules.
def add_browser_args_movies_style(parser: argparse.ArgumentParser) -> None:
    add_browser_args(parser)


def resolve_headless_movies_style(args: argparse.Namespace) -> bool:
    return resolve_headless(args, default_headless=False)


def add_browser_args_default_headless(parser: argparse.ArgumentParser) -> None:
    add_browser_args(parser)


def resolve_headless_default_headless(args: argparse.Namespace) -> bool:
    return resolve_headless(args, default_headless=True)
