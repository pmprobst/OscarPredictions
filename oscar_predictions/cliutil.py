"""Shared argparse helpers for CLI parity across scrapers."""

from __future__ import annotations

import argparse


def add_browser_args_movies_style(parser: argparse.ArgumentParser) -> None:
    """
    scrape_movies semantics: default is windowed (headed). Use --headless for no window.
    --headed is an explicit alias for the default (for consistency with other scripts).
    Mutually exclusive: at most one of --headless / --headed.
    """
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window.",
    )
    g.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible Chromium window (default for scrape_movies).",
    )


def resolve_headless_movies_style(args: argparse.Namespace) -> bool:
    """Return True if browser should run headless (scrape_movies family)."""
    if args.headless:
        return True
    if args.headed:
        return False
    return False


def add_browser_args_default_headless(parser: argparse.ArgumentParser) -> None:
    """
    scrape_actors / scrape_actor_awards semantics: default headless. --headed shows window.
    --headless is an explicit alias for the default (for consistency with scrape_movies).
    """
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible Chromium window (default: headless, no window).",
    )
    g.add_argument(
        "--headless",
        action="store_true",
        help="Run Chromium without opening a window (default for this script).",
    )


def resolve_headless_default_headless(args: argparse.Namespace) -> bool:
    """Return True if browser should run headless (default-headless scrapers)."""
    if args.headed:
        return False
    if args.headless:
        return True
    return True
