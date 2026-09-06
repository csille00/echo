"""Run Google Vision OCR on a test scan, with optional LLM cleanup."""

import argparse
import asyncio
import os
import sys
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from pdf2image import convert_from_path

from journal_search.adapters.ocr.google_vision import GoogleVisionOCR
from journal_search.adapters.text_cleanup.ai_sdk import AISDKTextCleanup
from journal_search.ports.text_cleanup import TextCleanupProvider

load_dotenv()


def load_image(path: Path) -> list[tuple[str, bytes]]:
    """Load image(s) from a file. Returns list of (name, bytes) tuples."""
    if path.suffix.lower() == ".pdf":
        images = convert_from_path(path)
        results = []
        for i, img in enumerate(images):
            buf = BytesIO()
            img.save(buf, format="PNG")
            results.append((f"{path.name} (page {i+1})", buf.getvalue()))
        return results
    return [(path.name, path.read_bytes())]


def create_cleanup_provider(provider: str, model: str) -> TextCleanupProvider:
    if provider == "openai":
        return AISDKTextCleanup(provider="openai", model=model)
    return AISDKTextCleanup(
        provider="ollama",
        model=model,
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Google Vision OCR on a test scan")
    parser.add_argument("image", nargs="?", help="Path to image file (defaults to first in test-data/)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("scripts/ocr-comparison-output.txt"),
        help="Path to write OCR output",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Run LLM cleanup on OCR output",
    )
    parser.add_argument(
        "--llm-provider",
        default=os.environ.get("LLM_PROVIDER", "ollama"),
        choices=["ollama", "openai"],
        help="LLM provider for cleanup (default: ollama)",
    )
    parser.add_argument(
        "--llm-model",
        default=os.environ.get("LLM_MODEL", "llama3.2"),
        help="LLM model for cleanup (default: llama3.2)",
    )
    args = parser.parse_args()

    if args.image:
        scan_path = Path(args.image)
        if not scan_path.is_file():
            print(f"File not found: {scan_path}")
            return
        scans = [scan_path]
    else:
        test_data = Path("test-data")
        scans = [
            p
            for p in sorted(test_data.iterdir())
            if p.is_file()
            and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp", ".pdf"}
        ][:1]

        if not scans:
            print("No image files found in test-data/")
            return

    cleanup: TextCleanupProvider | None = None
    if args.cleanup:
        cleanup = create_cleanup_provider(args.llm_provider, args.llm_model)

    def emit(text: str = "") -> None:
        print(text)
        out.write(text + "\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        emit(f"Running Google Vision on: {scans[0].name}")
        if args.cleanup:
            emit(f"LLM cleanup: {args.llm_provider}:{args.llm_model}")
        engine = GoogleVisionOCR()

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
                        cleaned = await cleanup.cleanup(result.text, source_model=result.model)
                        emit(f"Model: {cleaned.model}")
                        emit(f"Text:\n{cleaned.text}")
                except Exception as e:
                    emit(f"Error: {e}")
                sys.stdout.flush()

    print(f"\nWrote output to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
