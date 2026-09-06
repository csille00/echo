"""Shared helpers for OCR image handling."""

from io import BytesIO

from PIL import Image


def open_image(image_data: bytes, format_hint: str | None = None) -> Image.Image:
    """Open image bytes, optionally constraining the decoder format."""
    open_kwargs: dict[str, list[str]] = {}
    if format_hint:
        open_kwargs["formats"] = [format_hint.upper()]

    image = Image.open(BytesIO(image_data), **open_kwargs)
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image
