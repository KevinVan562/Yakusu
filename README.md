# Yakusu

Yakusu (訳す) is a modern, AI-powered manga translation workspace designed to streamline the scanlation workflow. It automates the tedious process of text detection, OCR, and typesetting, allowing you to go from raw Japanese scans to fully translated pages in seconds.

## Key Features

- **Automated Bubble Detection**: Uses YOLOv8 to precisely locate speech bubbles and text areas.
- **High-Accuracy OCR**: Powered by `manga-ocr` for reliable Japanese text recognition.
- **Flexible LLM Translation**: Support for Google Gemini, OpenAI, and local models via Ollama (defaulting to `gemma2:9b`).
- **Smart Typesetting**: Automatically clears original text and renders translations with dynamic font sizing to fit bubbles perfectly.
- **Modern UI**: A clean, centered React interface with full dark mode support.
- **Chapter Processing**: Batch process entire chapters and download the results as a ZIP.

## Screenshots

### Light Mode
![Light Mode](docs/images/light_mode.png)

### Dark Mode
![Dark Mode](docs/images/dark_mode.png)

### Results
![Results](docs/images/results.png)

## Local Setup

1. Copy environment files:

   ```bash
   cp services/api/.env.example services/api/.env
   cp apps/web/.env.example apps/web/.env
   ```

2. Install dependencies:

   ```bash
   npm run setup
   ```

3. If you are using local Ollama translation, start Ollama and make sure the model exists:

   ```bash
   ollama serve
   ollama pull gemma2:9b
   ```

4. Start the API:

   ```bash
   npm run dev:api
   ```

5. Start the web app in another terminal:

   ```bash
   npm run dev:web
   ```

The web app runs at `http://localhost:5173` unless Vite chooses another open port.
The local API runs at `http://127.0.0.1:8000`.

## Services

- `services/api`: FastAPI manga OCR and translation service deployed to Hugging Face Spaces.

## Apps

- `apps/web`: React + Vite frontend.
