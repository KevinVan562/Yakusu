---
title: Yakusu API
emoji: 📖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Yakusu API

Python microservice for manga page text extraction and LLM-powered translation rendering.

## Endpoints

- `POST /ocr`: accepts an uploaded manga page and returns a list of detected bubbles and their OCR text.
- `POST /translate`: accepts an uploaded manga page and returns a PNG with translated text rendered into detected bubbles. Supports Gemini, OpenAI, and Local LLMs (Ollama).

## Configuration

The API is configured via environment variables or a `.env` file:

- `YAKUSU_LLM_PROVIDER`: `gemini`, `openai`, or `local`.
- `YAKUSU_LLM_API_KEY`: Your API key (or `ollama` for local).
- `YAKUSU_LLM_MODEL_NAME`: e.g., `models/gemini-2.0-flash`, `gpt-4o`, or `llama3.2:latest`.
- `YAKUSU_LLM_BASE_URL`: (Optional) Custom endpoint for OpenAI-compatible APIs (default for local is `http://localhost:11434/v1`).

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Download bubble detection weights (YOLOv8) and place them in `models/manga-bubble-yolov8.pt`.

3. Run the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

## Usage Example

```bash
curl -X POST http://127.0.0.1:8000/translate \
  -F "file=@tests/testpanel.jpg" \
  -F "target_language=English" \
  -o translated_page.png
```
