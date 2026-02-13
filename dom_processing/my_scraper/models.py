from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, computed_field
from datetime import datetime


class InstanceMetadata(BaseModel):
    year: Optional[str] = None
    exam_variant: Optional[List[str]] = None
    subject: Optional[str] = None


class InstanceDocuments(BaseModel):
    exam_path: Optional[Path] = None
    exam_urls: Optional[list[str]] = None
    exam_entry_page_url: Optional[str] = None
    exam_page_count: Optional[int] = None

    solution_exists:Optional[bool] = False
    
    solution_path: Optional[Path] = None
    solution_urls: Optional[list[str]] = None
    solution_entry_page_url: Optional[str] = None
    solution_page_count: Optional[int] = None


class Instance(BaseModel):
    metadata: InstanceMetadata = Field(default_factory=InstanceMetadata)
    documents: InstanceDocuments = Field(default_factory=InstanceDocuments)
    
    # Scraping state
    scraping_status: Optional[str] = None  # "success", "failed", "partial"
    error_message: Optional[str] = None
    scraped_at: Optional[datetime] = None
    
    # Location
    country: Optional[str] = "china"
    province: Optional[str] = None
    language: Optional[str] = "Chinese"
    
    # File format
    file_format: Optional[str] = "pdf"
    
    @computed_field
    def year(self) -> Optional[str]:
        return self.metadata.year

    @computed_field
    def exam_variant(self) -> Optional[List[str]]:
        return self.metadata.exam_variant

    @computed_field
    def subject(self) -> Optional[str]:
        return self.metadata.subject

    @computed_field
    def exam_document_path(self) -> Optional[Path]:
        return self.documents.exam_path

    @computed_field
    def solution_document_path(self) -> Optional[Path]:
        return self.documents.solution_path
    
    @computed_field
    def solution_exists(self) -> bool:
        return self.documents.solution_url is not None or self.documents.solution_path is not None

