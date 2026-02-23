from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExamRecord:
    exam_id: Optional[int] = None
    country: Optional[str] = None
    language: Optional[str] = None
    province: Optional[str] = None
    subject: Optional[str] = None
    subject_en: Optional[str] = None
    exam_variant: Optional[str] = None
    exam_variant_en: Optional[str] = None
    year: Optional[int] = None
    exam_urls: Optional[list[str]] = None
    local_path: Optional[str] = None
    entry_page_url: Optional[str] = None  # fixed from entry_page_link
    file_format: Optional[str] = None
    page_count: Optional[int] = None
    solution_exists: Optional[bool] = None
    solution_id: Optional[int] = None
    scraped_at: Optional[datetime] = None
    scraping_status: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class SolutionRecord:
    solution_id: Optional[int] = None
    exam_id: Optional[int] = None
    solution_urls: Optional[list[str]] = None
    local_path: Optional[str] = None
    entry_page_url: Optional[str] = None  # fixed from entry_page_link
    file_format: Optional[str] = None
    page_count: Optional[int] = None
    scraped_at: Optional[datetime] = None
    scraping_status: Optional[str] = None
    error_message: Optional[str] = None