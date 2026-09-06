"""Run Google Vision OCR on a test scan, with optional LLM cleanup."""

import argparse
import asyncio
import sys
import traceback
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path

from journal_search.config import get_settings
from journal_search.dependencies import (
    create_ocr_provider,
    create_text_cleanup_provider,
)


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


async def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()

    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run Google Vision OCR on a test scan")
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
        help="Run LLM cleanup on OCR output",
    )
    parser.add_argument(
        "--llm-provider",
        default=settings.llm_provider.value,
        choices=["ollama", "openai"],
        help="LLM provider for cleanup",
    )
    parser.add_argument(
        "--llm-model",
        default=settings.llm_model,
        help="LLM model for cleanup",
    )
    args = parser.parse_args()

    if args.image:
        scan_path = Path(args.image)
        if not scan_path.is_file():
            print(f"File not found: {scan_path}")
            sys.exit(1)
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
            sys.exit(1)

    cleanup = None
    if args.cleanup:
        cleanup_kwargs: dict[str, str | None] = {"model": args.llm_model}
        if args.llm_provider == "ollama":
            cleanup_kwargs["base_url"] = settings.ollama_base_url
        elif args.llm_provider == "openai":
            if settings.openai_api_key is None:
                print("OPENAI_API_KEY is required for OpenAI cleanup")
                sys.exit(1)
            cleanup_kwargs["api_key"] = settings.openai_api_key.get_secret_value()
        cleanup = create_text_cleanup_provider(args.llm_provider, **cleanup_kwargs)

    def emit(text: str = "") -> None:
        print(text)
        out.write(text + "\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        emit(f"Running Google Vision on: {scans[0].name}")
        if args.cleanup:
            emit(f"LLM cleanup: {args.llm_provider}:{args.llm_model}")

        api_key = (
            settings.google_vision_api_key.get_secret_value()
            if settings.google_vision_api_key is not None
            else None
        )
        engine = create_ocr_provider(
            "google_vision",
            api_key=api_key,
            credentials_file=settings.google_vision_credentials_file,
        )

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
                            cleaned = await cleanup.cleanup(result.text, source_model=result.model)
                            emit(f"Model: {cleaned.model}")
                            emit(f"Text:\n{cleaned.text}")
                    except (RuntimeError, ValueError, OSError) as e:
                        emit(f"Error: {e}")
                        emit(traceback.format_exc())
                    sys.stdout.flush()
        finally:
            if hasattr(engine, "close"):
                await engine.close()

    print(f"\nWrote output to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
