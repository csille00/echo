"""Run OCR on a test scan, with optional LLM cleanup driven by .env settings."""

import argparse
import asyncio
import sys
import traceback
from io import BytesIO
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pdf2image import convert_from_path

from journal_search.adapters.ai_sdk.factory import create_ai_sdk_from_settings
from journal_search.config import get_settings
from journal_search.dependencies import (
    create_ocr_provider_from_settings,
    create_text_cleanup_provider_from_settings,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_image(path: Path) -> list[tuple[str, bytes]]:
    """Load image(s) from a file. Returns list of (name, bytes) tuples."""
    if path.suffix.lower() == ".pdf":
        images = convert_from_path(path)
        results = []
        for i, img in enumerate(images):
            buf = BytesIO()
            img.save(buf, format="PNG")
            results.append((f"{path.name} (page {i + 1})", buf.getvalue()))
        return results
    return [(path.name, path.read_bytes())]


def resolve_cleanup_enabled(args: argparse.Namespace, settings_enabled: bool) -> bool:
    """CLI flags override LLM_CLEANUP_ENABLED from .env."""
    if args.no_cleanup:
        return False
    if args.cleanup:
        return True
    return settings_enabled


async def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Run OCR on a test scan using OCR_PROVIDER and LLM settings from .env",
    )
    parser.add_argument(
        "image",
        nargs="?",
        help="Path to image file (defaults to first in test-data/)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("scripts/ocr-output.txt"),
        help="Path to write OCR output",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Force LLM cleanup on (overrides LLM_CLEANUP_ENABLED)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Force LLM cleanup off (overrides LLM_CLEANUP_ENABLED)",
    )
    args = parser.parse_args()

    if args.cleanup and args.no_cleanup:
        print("Use only one of --cleanup or --no-cleanup")
        sys.exit(1)

    cleanup_enabled = resolve_cleanup_enabled(args, settings.llm_cleanup_enabled)

    if args.image:
        scan_path = Path(args.image)
        if not scan_path.is_file():
            print(f"File not found: {scan_path}")
            sys.exit(1)
        scans = [scan_path]
    else:
        test_data = PROJECT_ROOT / "test-data"
        scans = [
            p
            for p in sorted(test_data.iterdir())
            if p.is_file()
            and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp", ".pdf"}
        ][:1]

        if not scans:
            print(f"No image files found in {test_data}")
            sys.exit(1)

    cleanup = None
    ai_sdk = create_ai_sdk_from_settings(settings)
    if cleanup_enabled:
        cleanup = create_text_cleanup_provider_from_settings(
            settings,
            ai_sdk,
            enabled=True,
        )
        if cleanup is None:
            print(
                "LLM cleanup is enabled but could not be configured. "
                "Check LLM_PROVIDER and API keys."
            )
            sys.exit(1)

    engine = create_ocr_provider_from_settings(settings)

    def emit(text: str = "") -> None:
        print(text)
        out.write(text + "\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        emit(f"OCR provider: {settings.ocr_provider.value}")
        emit(f"Running on: {scans[0].name}")
        if cleanup:
            emit(f"LLM cleanup: {settings.llm_provider.value}:{settings.llm_model}")
        else:
            emit("LLM cleanup: disabled")

        try:
            for scan_path in scans:
                emit("=" * 80)
                emit(f"FILE: {scan_path.name}")
                emit("=" * 80)

                for img_name, img_data in load_image(scan_path):
                    emit(f"\n>>> {img_name}")

                    emit("\n--- RAW OCR ---")
                    try:
                        result = await engine.extract(img_data)
                        conf_str = f"{result.confidence:.1%}" if result.confidence else "N/A"
                        emit(f"Confidence: {conf_str}")
                        emit(f"Text:\n{result.text}")

                        if cleanup:
                            emit("\n--- CLEANED ---")
                            try:
                                cleaned = await cleanup.cleanup(
                                    result.text,
                                    source_model=result.model,
                                )
                                emit(f"Model: {cleaned.model}")
                                emit(f"Text:\n{cleaned.text}")
                            except Exception as e:
                                emit(f"Cleanup error: {e}")
                                emit(traceback.format_exc())
                    except (RuntimeError, ValueError, OSError, httpx.HTTPError) as e:
                        emit(f"Error: {e}")
                        emit(traceback.format_exc())
                    sys.stdout.flush()
        finally:
            if hasattr(engine, "close"):
                await engine.close()

    print(f"\nWrote output to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
