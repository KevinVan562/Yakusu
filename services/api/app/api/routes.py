from __future__ import annotations

import io
import zipfile
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from typing import List

from app.models.schemas import MangaOcrResponse
from app.services.pipeline import pipeline

router = APIRouter()

async def load_uploaded_image(file: UploadFile) -> Image.Image:
    """Validate and normalize a multipart upload into an RGB PIL image."""
    # Read the file content
    request_object_content = await file.read()

    try:
        # Open the image using PIL
        with Image.open(io.BytesIO(request_object_content)) as uploaded_image:
            # Fix orientation and convert to RGB
            return ImageOps.exif_transpose(uploaded_image).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"File {file.filename} is not a valid image.") from exc

@router.post("/ocr", response_model=MangaOcrResponse)
async def process_ocr(file: UploadFile = File(...)):
    img = await load_uploaded_image(file)

    try:
        # `/ocr` is the stable machine-readable endpoint for the frontend/Supabase flow.
        detected_blocks = pipeline.extract_blocks(img)
        return MangaOcrResponse(
            filename=file.filename or "upload",
            width=img.width,
            height=img.height,
            blocks=detected_blocks,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR execution failed: {exc}") from exc

@router.post("/translate")
async def process_translation(
    file: UploadFile = File(...),
    target_language: str = Form("English"),
    llm_provider: str | None = Form(None),
    llm_api_key: str | None = Form(None),
    llm_model_name: str | None = Form(None),
    llm_base_url: str | None = Form(None),
) -> Response:
    img = await load_uploaded_image(file)

    try:
        translated_image = pipeline.render_translation(
            img,
            target_language=target_language,
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            llm_model_name=llm_model_name,
            llm_base_url=llm_base_url,
        )
        output = io.BytesIO()
        translated_image.save(output, format="PNG")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Translation rendering failed: {exc}",
        ) from exc

    filename = file.filename or "upload"
    safe_stem = filename.rsplit(".", maxsplit=1)[0] or "upload"
    headers = {
        "Content-Disposition": f'inline; filename="{safe_stem}-translated.png"',
    }
    return Response(content=output.getvalue(), media_type="image/png", headers=headers)

@router.post("/translate/batch")
async def process_batch_translation(
    files: List[UploadFile] = File(...),
    target_language: str = Form("English"),
    llm_provider: str | None = Form(None),
    llm_api_key: str | None = Form(None),
    llm_model_name: str | None = Form(None),
    llm_base_url: str | None = Form(None),
) -> Response:
    """
    Accepts a list of images and returns a ZIP file containing 
    all translated pages in the same order they were uploaded.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # We will store the resulting image data in memory
    zip_buffer = io.BytesIO()

    try:
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for i, file in enumerate(files):
                # 1. Load the image
                img = await load_uploaded_image(file)

                # 2. Process translation
                translated_img = pipeline.render_translation(
                    img,
                    target_language=target_language,
                    llm_provider=llm_provider,
                    llm_api_key=llm_api_key,
                    llm_model_name=llm_model_name,
                    llm_base_url=llm_base_url,
                )
                
                # 3. Save to a byte buffer
                img_byte_arr = io.BytesIO()
                translated_img.save(img_byte_arr, format="PNG")
                
                # 4. Add to ZIP (naming them 001.png, 002.png etc to keep order)
                file_name = f"{i+1:03d}.png"
                zip_file.writestr(file_name, img_byte_arr.getvalue())

        # Reset buffer for reading
        zip_buffer.seek(0)
        
        headers = {
            "Content-Disposition": 'attachment; filename="translated_chapter.zip"',
        }
        return Response(
            content=zip_buffer.getvalue(), 
            media_type="application/x-zip-compressed", 
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {e}")
