"""Quick script to test OCR on a scan."""

import asyncio
import io
import sys
from pathlib import Path

from pdf2image import convert_from_path

from journal_search.adapters.ocr.tesseract import TesseractOCR


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_ocr.py <pdf_or_image_path>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    ocr = TesseractOCR()

    if path.suffix.lower() == ".pdf":
        print(f"Converting PDF to images: {path}")
        images = convert_from_path(path)
        print(f"Found {len(images)} page(s)")

        for i, image in enumerate(images):
            print(f"\n--- Page {i + 1} ---")
            # Convert PIL image to bytes
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            image_data = buf.getvalue()

            result = await ocr.extract(image_data)
            print(f"Confidence: {result.confidence:.2%}" if result.confidence else "Confidence: N/A")
            print(f"Text:\n{result.text}")
    else:
        print(f"Processing image: {path}")
        image_data = path.read_bytes()
        result = await ocr.extract(image_data)
        print(f"Confidence: {result.confidence:.2%}" if result.confidence else "Confidence: N/A")
        print(f"Text:\n{result.text}")


if __name__ == "__main__":
    asyncio.run(main())
