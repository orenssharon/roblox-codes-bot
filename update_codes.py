#!/usr/bin/env python3
"""
Roblox Codes Aggregator
- Fetches several public code-list sources.
- Extracts code candidates from pages.
- Cross-checks candidates across sources.
- Never claims a code is redeemable just because a website lists it.
- Writes roblox-codes.json atomically; preserves the last good file on total fetch failure.

Install:
    pip install requests beautifulsoup4

Run:
    python roblox_codes.py
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = Path("roblox-codes.json")
MIN_SOURCE_COUNT = int(os.getenv("MIN_SOURCE_COUNT", "2"))
REQUEST_TIMEOUT = 25

# These are public editorial sources, not official Roblox validation endpoints.
# Add sources only after checking their quality and terms of use.
SOURCES = [
    {
        "name": "GamesRadar",
        "url": "https://www.gamesradar.com/roblox-promo-codes/",
        "kind": "global_and_experience",
    },
    {
        "name": "iGeeksBlog",
        "url": "https://www.igeeksblog.com/roblox-promo-codes/",
        "kind": "global_and_experience",
    },
    {
        "name": "TheTechBasket",
        "url": "https://www.thetechbasket.com/promo-codes/",
        "kind": "global_and_experience",
    },
    {
        "name": "CouponVPS",
        "url": "https://couponvps.com/roblox-promo-codes/",
        "kind": "global_and_experience",
    },
]

# Known expired codes are excluded from the active-reported result even if
# an old page still contains them. This list should be maintained carefully.
KNOWN_EXPIRED = {
    "TWEETROBLOX", "ROBLOXEDU2021", "FREENGNBOI", "FREENGNGON",
    "100MILSEGUIDORES", "AMAZONFRIEND2021", "CARREFOURHOED2021",
    "ECONOMYEVENT2021", "FREEAMAZONFOX2022", "FREETARGETSANTA2022",
    "KROGERDAYS2021", "MERCADOLIBREFEDORA2021", "ROSSMANNCROWN2021",
    "TARGETMINTHAT2021", "WALMARTMEXEARS2021",
}

# Common page words that can look like codes. Keep this list conservative:
# aggressive blocklists can accidentally remove genuine codes.
BLOCKLIST = {
    "ROBLOX", "PROMO", "CODES", "CODE", "ACTIVE", "EXPIRED", "WORKING",
    "LATEST", "OCTOBER", "NOVEMBER", "DECEMBER", "JANUARY", "FEBRUARY",
    "MARCH", "APRIL", "AUGUST", "SEPTEMBER", "OCTOBER", "GUIDE",
    "REDEEM", "REWARDS", "REWARD", "FREE", "ITEMS", "ITEM", "UPDATED",
    "WORKINGCODES", "ALLCODES", "COPYALLCODES", "ISLANDOFMOVE",
    "MANSIONOFWONDER", "HTML", "DOCTYPE", "HTTP", "HTTPS", "WWW",
}

# Explicit classification helps distinguish platform-wide promo codes from
# codes entered inside a particular Roblox experience.
KNOWN_CODES = {
    "SPIDERCOLA": {
        "reward": "Spider Cola shoulder accessory",
        "scope": "global",
    },
    "DIY": {
        "reward": "Kinetic Staff",
        "scope": "Island of Move",
    },
    "GETMOVING": {
        "reward": "Speedy Shades",
        "scope": "Island of Move",
    },
    "SETTINGTHESTAGE": {
        "reward": "Build It Backpack",
        "scope": "Island of Move",
    },
    "STRIKEAPOSE": {
        "reward": "Hustle Hat",
        "scope": "Island of Move",
    },
    "VICTORYLAP": {
        "reward": "Cardio Cans",
        "scope": "Island of Move",
    },
    "WORLDALIVE": {
        "reward": "Crystalline Companion",
        "scope": "Island of Move",
    },
    "BOARDWALK": {
        "reward": "Ring of Flames",
        "scope": "Mansion of Wonder",
    },
    "FXARTIST": {
        "reward": "Artist Backpack",
        "scope": "Mansion of Wonder",
    },
    "GLIMMER": {
        "reward": "Head Slime",
        "scope": "Mansion of Wonder",
    },
    "PARTICLEWIZARD": {
        "reward": "Tome of the Magus",
        "scope": "Mansion of Wonder",
    },
    "THINGSGOBOOM": {
        "reward": "Ghastly Aura",
        "scope": "Mansion of Wonder",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RobloxCodesResearchBot/1.0; "
        "+https://www.smartchoicelinks.com/)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_code(value: str) -> str | None:
    value = value.strip().strip("`'\"“”‘’.,:;()[]{}<>")
    if not value:
        return None

    # Preserve ! and $ only when they are part of a plausible token.
    value = value.upper()
    if not 3 <= len(value) <= 30:
        return None
    if value in BLOCKLIST or value in KNOWN_EXPIRED:
        return None
    if not re.fullmatch(r"[A-Z0-9!$_-]+", value):
        return None
    if not re.search(r"[A-Z]", value):
        return None
    # Avoid ordinary words and dates. Accept mixed alphanumeric codes,
    # or known legacy experience codes that are word-shaped.
    if value.isalpha() and value not in KNOWN_CODES:
        return None
    if re.fullmatch(r"(19|20)\d{2}", value):
        return None
    return value


def fetch_page(session: requests.Session, source: dict[str, str]) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] = {
        "name": source["name"],
        "url": source["url"],
        "fetched_at": utc_now(),
        "success": False,
        "http_status": None,
        "candidates": [],
        "error": None,
    }

    try:
        response = session.get(
            source["url"],
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        result["http_status"] = response.status_code
        response.raise_for_status()

        # Avoid treating an access-denied/challenge page as a valid source.
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type and "<html" not in response.text[:1000].lower():
            raise ValueError(f"Unexpected content type: {content_type or 'unknown'}")

        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
            node.decompose()

        # Keep visible page text, including code tables and inline code tags.
        page_text = soup.get_text(" ", strip=True).upper()

        # Token candidates include punctuation used by a small number of old codes.
        raw_candidates = re.findall(
            r"(?<![A-Z0-9])[!$]?[A-Z0-9][A-Z0-9!$_-]{2,28}(?![A-Z0-9])",
            page_text,
        )

        candidates = set()
        for raw in raw_candidates:
            candidate = normalize_code(raw)
            if candidate:
                candidates.add(candidate)

        # Some pages format codes as <code> or table cells. Include those
        # elements explicitly; the general page-text pass remains a fallback.
        for node in soup.select("code, td, th"):
            candidate = normalize_code(node.get_text(" ", strip=True))
            if candidate:
                candidates.add(candidate)

        result["candidates"] = sorted(candidates)
        result["success"] = True
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        return result

    except (requests.RequestException, ValueError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        return result


def load_previous(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    previous = load_previous(OUTPUT_FILE)
    session = requests.Session()

    source_results = []
    for source in SOURCES:
        result = fetch_page(session, source)
        source_results.append(result)
        print(
            f"[{'OK' if result['success'] else 'FAIL'}] "
            f"{source['name']}: HTTP={result['http_status']} "
            f"candidates={len(result['candidates'])} "
            f"error={result['error'] or '-'}"
        )

    successful_sources = [item for item in source_results if item["success"]]

    # Do not overwrite a good file with an empty result if every source failed.
    if not successful_sources:
        print("ERROR: all sources failed; preserving existing JSON.")
        return 2

    sightings: dict[str, list[dict[str, str]]] = {}
    for result in successful_sources:
        for code in result["candidates"]:
            sightings.setdefault(code, []).append({
                "source": result["name"],
                "url": result["url"],
                "observed_at": result["fetched_at"],
            })

    codes = []
    for code, found_in in sorted(sightings.items()):
        if len(found_in) < MIN_SOURCE_COUNT:
            continue

        # If a code appears on known-expired pages only, it is filtered above.
        # Source consensus is evidence of reporting, not proof of redemption.
        metadata = KNOWN_CODES.get(code, {})
        codes.append({
            "code": code,
            "reward": metadata.get("reward", "Reward not independently confirmed"),
            "scope": metadata.get("scope", "unknown"),
            "status": (
                "reported_active_unverified"
                if code not in KNOWN_EXPIRED
                else "expired"
            ),
            "source_count": len(found_in),
            "sources": found_in,
            "verification": (
                "Cross-listed by multiple editorial sources; "
                "not directly verified with Roblox redemption."
            ),
            "first_seen_in_this_run": utc_now(),
        })

    # Put better-supported and known codes first.
    codes.sort(
        key=lambda item: (
            item["source_count"],
            item["code"] in KNOWN_CODES,
        ),
        reverse=True,
    )

    output = {
        "schema_version": 2,
        "last_updated": utc_now(),
        "sources_checked": len(source_results),
        "sources_succeeded": len(successful_sources),
        "minimum_sources_required": MIN_SOURCE_COUNT,
        "total_discovered": len(sightings),
        "total_cross_listed": len(codes),
        "codes": codes,
        "source_health": [
            {
                "name": item["name"],
                "url": item["url"],
                "success": item["success"],
                "http_status": item["http_status"],
                "candidate_count": len(item["candidates"]),
                "error": item["error"],
                "fetched_at": item["fetched_at"],
            }
            for item in source_results
        ],
        "important_note": (
            "Cross-source agreement does not prove a code is redeemable. "
            "Roblox promo codes can expire and must be tested on Roblox. "
            "Codes for Island of Move and Mansion of Wonder are redeemed "
            "inside those experiences, not on the global promo page."
        ),
    }

    # Keep a backup of the previous data if the new successful fetch yields
    # no cross-listed codes; the current run's health report is still saved
    # separately so the failure is visible.
    if not codes and previous and previous.get("codes"):
        output["previous_codes_preserved"] = True
        output["previous_codes"] = previous["codes"]
        print(
            "WARNING: no codes passed cross-source threshold. "
            "Previous codes are included for diagnostics, not labeled active."
        )

    atomic_write_json(OUTPUT_FILE, output)
    print(
        f"Saved {len(codes)} cross-listed candidates to {OUTPUT_FILE}. "
        f"Successful sources: {len(successful_sources)}/{len(SOURCES)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
