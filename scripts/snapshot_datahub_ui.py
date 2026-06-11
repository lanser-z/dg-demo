"""Snapshot the DataHub UI for the teaching notebook (one-off, manual).

Run:
    uv run python scripts/snapshot_datahub_ui.py

Output (3 PNGs):
    screenshots/datahub_01_home.png
    screenshots/datahub_02_search_lims.png
    screenshots/datahub_03_lims_samples.png

If DataHub is unreachable, write `screenshots/datahub_UNAVAILABLE.txt` with
the reason so the notebook can still display a graceful "see local file"
fallback.

This is a developer/authoring tool, not part of the notebook runtime.
The notebook itself embeds the screenshot paths as markdown images and
fails gracefully if the PNG is missing.
"""
from __future__ import annotations

import sys
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "screenshots"
DATAHUB_URL = "http://localhost:29002"

SHOTS: list[tuple[str, str, str]] = [
    # (filename_suffix, label, url_path)
    # NOTE: DataHub v1.x renders `/` as a near-blank splash page; `/search` is
    # what new users actually see as the landing view, so we use that as "首页".
    ("01_home", "DataHub 搜索首页（也是落地页）", "/search"),
    ("02_search_lims", "搜索 lims 后的结果", "/search?page=1&query=lims"),
    ("03_lims_samples", "LIMS 样品 dataset 详情", "/dataset/urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)"),
]


def _datahub_alive() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(f"{DATAHUB_URL}/", timeout=3) as r:
            return (r.status == 200, f"HTTP {r.status}")
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        return (False, f"{type(e).__name__}: {e}")


def _fallback_unavailable(reason: str) -> None:
    note = SCREENSHOT_DIR / "datahub_UNAVAILABLE.txt"
    note.write_text(
        f"DataHub UI screenshots were NOT generated.\n"
        f"Reason: {reason}\n"
        f"Re-run: uv run python scripts/snapshot_datahub_ui.py\n",
        encoding="utf-8",
    )
    print(f"[snapshot] wrote fallback note: {note}")


def _snapshot_with_playwright() -> None:
    """Use Playwright to log in once and capture 3 screenshots."""
    from playwright.sync_api import sync_playwright

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Step 1: home — DataHub redirects unauthenticated users to /login,
        # so we land there first, authenticate, then return to the home page.
        page.goto(f"{DATAHUB_URL}/login", wait_until="domcontentloaded", timeout=15_000)
        page.wait_for_selector("#username", timeout=10_000)
        page.fill("#username", "datahub")
        page.fill("#password", "datahub")
        page.click('button:has-text("Login")')
        page.wait_for_load_state("networkidle", timeout=15_000)
        # Now navigate to the home search view (DataHub v1.x renders `/` as
        # a near-blank splash; `/search` is what users see as the landing).
        page.goto(f"{DATAHUB_URL}/search", wait_until="networkidle", timeout=15_000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SCREENSHOT_DIR / "datahub_01_home.png"), full_page=False)
        print(f"[snapshot] saved datahub_01_home.png  ({SHOTS[0][1]})")

        # Step 2: search 'lims'
        page.goto(f"{DATAHUB_URL}/search?page=1&query=lims", wait_until="networkidle", timeout=15_000)
        page.wait_for_timeout(1500)  # let the search results render
        page.screenshot(path=str(SCREENSHOT_DIR / "datahub_02_search_lims.png"), full_page=False)
        print(f"[snapshot] saved datahub_02_search_lims.png  ({SHOTS[1][1]})")

        # Step 3: lims/samples detail
        page.goto(
            f"{DATAHUB_URL}/dataset/urn:li:dataset:(urn:li:dataPlatform:lims,samples,PROD)",
            wait_until="networkidle",
            timeout=15_000,
        )
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SCREENSHOT_DIR / "datahub_03_lims_samples.png"), full_page=False)
        print(f"[snapshot] saved datahub_03_lims_samples.png  ({SHOTS[2][1]})")

        browser.close()


def main() -> int:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    alive, info = _datahub_alive()
    if not alive:
        print(f"[snapshot] DataHub at {DATAHUB_URL} not reachable: {info}")
        _fallback_unavailable(info)
        return 1
    print(f"[snapshot] DataHub reachable ({info}), launching Playwright")
    try:
        _snapshot_with_playwright()
    except Exception as e:  # noqa: BLE001 — best-effort dev tool
        print(f"[snapshot] Playwright failed: {type(e).__name__}: {e}")
        _fallback_unavailable(f"{type(e).__name__}: {e}")
        return 2
    print("[snapshot] done. Verify sizes: 100KB <= PNG <= 1MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
