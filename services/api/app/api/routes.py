from __future__ import annotations

import io
import zipfile
from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from typing import List

from app.models.schemas import MangaOcrResponse, TranslationJobPage, TranslationJobStatusResponse
from app.services.pipeline import pipeline
from app.services.translation_jobs import translation_jobs

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


def build_translation_job_response(job: dict, request: Request) -> TranslationJobStatusResponse:
    job_id = job["job_id"]
    completed_pages = int(job["completed_pages"])
    total_pages = int(job["total_pages"])

    pages = []
    for page_number in range(1, completed_pages + 1):
        pages.append(
            TranslationJobPage(
                page=page_number,
                url=str(
                    request.url_for(
                        "get_translation_job_page",
                        job_id=job_id,
                        page_number=page_number,
                    )
                ),
            )
        )

    result_zip_url = None
    if job["status"] == "completed":
        result_zip_url = str(request.url_for("get_translation_job_zip", job_id=job_id))

    return TranslationJobStatusResponse(
        job_id=job_id,
        status=job["status"],
        total_pages=total_pages,
        completed_pages=completed_pages,
        target_language=job["target_language"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        error=job.get("error"),
        pages=pages,
        result_zip_url=result_zip_url,
    )


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


@router.post("/translate/jobs", response_model=TranslationJobStatusResponse, status_code=202)
async def create_translation_job(
    background_tasks: BackgroundTasks,
    request: Request,
    files: List[UploadFile] = File(...),
    target_language: str = Form("English"),
    llm_provider: str | None = Form(None),
    llm_api_key: str | None = Form(None),
    llm_model_name: str | None = Form(None),
    llm_base_url: str | None = Form(None),
) -> TranslationJobStatusResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    job = translation_jobs.create_job(total_pages=len(files), target_language=target_language)
    job_id = job["job_id"]

    try:
        for page_number, file in enumerate(files, start=1):
            img = await load_uploaded_image(file)
            img.save(translation_jobs.input_path(job_id, page_number), format="PNG")
    except HTTPException as exc:
        translation_jobs.fail_job(job_id, str(exc.detail))
        raise
    except Exception as exc:
        translation_jobs.fail_job(job_id, str(exc))
        raise HTTPException(status_code=500, detail=f"Job upload failed: {exc}") from exc

    background_tasks.add_task(
        translation_jobs.process_job,
        job_id,
        target_language,
        llm_provider,
        llm_api_key,
        llm_model_name,
        llm_base_url,
    )

    return build_translation_job_response(job, request)


@router.get("/translate/jobs/{job_id}", response_model=TranslationJobStatusResponse)
async def get_translation_job(job_id: str, request: Request) -> TranslationJobStatusResponse:
    try:
        job = translation_jobs.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Translation job not found.") from exc

    return build_translation_job_response(job, request)


@router.get("/translate/jobs/{job_id}/pages/{page_number}", name="get_translation_job_page")
async def get_translation_job_page(job_id: str, page_number: int) -> FileResponse:
    try:
        job = translation_jobs.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Translation job not found.") from exc

    if page_number < 1 or page_number > int(job["total_pages"]):
        raise HTTPException(status_code=404, detail="Page not found.")

    output_path = translation_jobs.output_path(job_id, page_number)
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Translated page is not ready.")

    return FileResponse(
        output_path,
        media_type="image/png",
        filename=f"{page_number:03d}.png",
    )


@router.get("/translate/jobs/{job_id}/result.zip", name="get_translation_job_zip")
async def get_translation_job_zip(job_id: str) -> Response:
    try:
        job = translation_jobs.get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Translation job not found.") from exc

    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Translation job is not completed.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for page_number in range(1, int(job["total_pages"]) + 1):
            output_path = translation_jobs.output_path(job_id, page_number)
            if not output_path.exists():
                raise HTTPException(status_code=500, detail=f"Translated page {page_number} is missing.")

            zip_file.write(output_path, arcname=f"{page_number:03d}.png")

    zip_buffer.seek(0)
    headers = {
        "Content-Disposition": 'attachment; filename="translated_chapter.zip"',
    }
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/x-zip-compressed",
        headers=headers,
    )


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
