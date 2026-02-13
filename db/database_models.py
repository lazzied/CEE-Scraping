from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExamRecord:
    """Database representation of an exam."""
    # Auto-generated
    exam_id: Optional[int] = None
    
    # Location metadata
    country: Optional[str] = None
    language: Optional[str] = None
    province: Optional[str] = None
    
    # Exam metadata (multilingual)
    subject: Optional[str] = None
    subject_en: Optional[str] = None
    exam_variant: Optional[str] = None
    exam_variant_en: Optional[str] = None
    year: Optional[int] = None
    
    # URLs and paths
    exam_urls: Optional[list[str]] = None
    local_path: Optional[str] = None
    entry_page_link: Optional[str] = None
    
    # File metadata
    file_format: Optional[str] = None
    page_count: Optional[int] = None
    
    # Solution relationship
    solution_exist: Optional[bool] = None
    solution_id: Optional[int] = None
    
    # Scraping metadata
    scraped_at: Optional[datetime] = None
    scraping_status: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class SolutionRecord:
    """Database representation of a solution."""
    # Auto-generated
    solution_id: Optional[int] = None
    exam_id: Optional[int] = None
    
    # URLs and paths
    solution_urls: Optional[list[str]] = None
    local_path: Optional[str] = None
    entry_page_link: Optional[str] = None
    
    # File metadata
    file_format: Optional[str] = None
    page_count: Optional[int] = None
    
    # Scraping metadata
    scraped_at: Optional[datetime] = None
    scraping_status: Optional[str] = None
    error_message: Optional[str] = None