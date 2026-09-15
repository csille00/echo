#!/usr/bin/env python3
"""Upload a test image and poll until processing completes."""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx

DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the journal processing pipeline")
    parser.add_argument("image", type=Path, help="Journal page image to upload")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--user-id", type=UUID, default=DEFAULT_USER_ID)
    parser.add_argument("--timeout", type=int, default=300, help="Max seconds to wait")
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"Image not found: {args.image}", file=sys.stderr)
        return 1

    headers = {"X-User-ID": str(args.user_id)}
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0) as client:
        health = await client.get("/health")
        health.raise_for_status()

        with args.image.open("rb") as f:
            response = await client.post(
                "/api/v1/entries/upload",
                headers=headers,
                files={"file": (args.image.name, f, "image/jpeg")},
            )
        response.raise_for_status()
        payload = response.json()
        entry_id = payload["entry_id"]
        print(f"Started workflow for entry {entry_id}")

        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            entry_resp = await client.get(f"/api/v1/entries/{entry_id}", headers=headers)
            entry_resp.raise_for_status()
            entry = entry_resp.json()
            status = entry["processing_status"]
            print(f"  status: {status}")

            if status == "completed":
                text = entry.get("extracted_text") or ""
                preview = text[:200].replace("\n", " ")
                print(f"Done. Text preview: {preview!r}")
                return 0
            if status == "failed":
                print("Processing failed.", file=sys.stderr)
                return 1

            await asyncio.sleep(2)

    print("Timed out waiting for processing.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
