from __future__ import annotations

import json
import uuid
from datetime import datetime

from PIL import Image

from app.core.config import get_settings
from app.services.pipeline import pipeline


class TranslationJobManager:
    """
    Stores chapter translation jobs on disk.
    The frontend can keep asking for the job status while pages are being translated.
    """

    def __init__(self):
        self.settings = get_settings()
        self.jobs_folder = self.settings.cache_root / "translation_jobs"
        self.jobs_folder.mkdir(parents=True, exist_ok=True)

    def create_job(self, total_pages: int, target_language: str) -> dict:
        job_id = uuid.uuid4().hex
        job_folder = self.job_folder(job_id)
        (job_folder / "input").mkdir(parents=True, exist_ok=True)
        (job_folder / "output").mkdir(parents=True, exist_ok=True)

        now = self.now()
        job = {
            "job_id": job_id,
            "status": "queued",
            "total_pages": total_pages,
            "completed_pages": 0,
            "target_language": target_language,
            "created_at": now,
            "updated_at": now,
            "error": None,
        }
        self.save_job(job)
        return job

    def job_folder(self, job_id: str):
        # Avoid letting a bad job id escape the jobs folder.
        if "/" in job_id or ".." in job_id:
            raise KeyError(job_id)
        return self.jobs_folder / job_id

    def input_path(self, job_id: str, page_number: int):
        return self.job_folder(job_id) / "input" / f"{page_number:03d}.png"

    def output_path(self, job_id: str, page_number: int):
        return self.job_folder(job_id) / "output" / f"{page_number:03d}.png"

    def get_job(self, job_id: str) -> dict:
        metadata_path = self.job_folder(job_id) / "metadata.json"
        if not metadata_path.exists():
            raise KeyError(job_id)

        with metadata_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_job(self, job: dict):
        job["updated_at"] = self.now()
        metadata_path = self.job_folder(job["job_id"]) / "metadata.json"

        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False, indent=2)

    def fail_job(self, job_id: str, error: str):
        job = self.get_job(job_id)
        job["status"] = "failed"
        job["error"] = error
        self.save_job(job)

    def process_job(
        self,
        job_id: str,
        target_language: str,
        llm_provider: str | None = None,
        llm_api_key: str | None = None,
        llm_model_name: str | None = None,
        llm_base_url: str | None = None,
    ):
        job = self.get_job(job_id)
        job["status"] = "running"
        job["error"] = None
        self.save_job(job)

        try:
            total_pages = int(job["total_pages"])
            for page_number in range(1, total_pages + 1):
                input_path = self.input_path(job_id, page_number)
                output_path = self.output_path(job_id, page_number)

                with Image.open(input_path) as source_image:
                    translated_image = pipeline.render_translation(
                        source_image.convert("RGB"),
                        target_language=target_language,
                        llm_provider=llm_provider,
                        llm_api_key=llm_api_key,
                        llm_model_name=llm_model_name,
                        llm_base_url=llm_base_url,
                    )
                    translated_image.save(output_path, format="PNG")

                job["completed_pages"] = page_number
                self.save_job(job)

            job["status"] = "completed"
            self.save_job(job)
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            self.save_job(job)

    def now(self) -> str:
        return datetime.utcnow().isoformat()


translation_jobs = TranslationJobManager()
