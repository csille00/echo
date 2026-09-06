# Journal Search

AI-powered journal OCR and semantic search.

## Development

```bash
nix-shell -p uv --run "uv venv && uv pip install -e '.[dev,ocr-tesseract]'"
source .venv/bin/activate
```

## Usage

```bash
python -m journal_search
```
