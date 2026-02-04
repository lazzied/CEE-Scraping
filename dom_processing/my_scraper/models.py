"""
Data models and enums for the scraping system.
"""

from pathlib import Path
from typing import Union, Optional, List
from dataclasses import dataclass
from enum import Enum
from pydantic import BaseModel, computed_field


class MetadataTypes(Enum):
    """Types of metadata that can be extracted from DOM nodes."""
    EXAM = "exam"
    SOLUTION = "solution"
    YEAR = "year"
    EXAM_VARIANT = "exam_variant"
    SUBJECT = "subject"


class DocumentContent(Enum):
    """Types of document content."""
    EXAM = "exam"
    SOLUTION = "solution"
    BOTH = "exam_and_solution"


@dataclass(frozen=True)
class ScrapingConfig:
    """Configuration for scraping behavior."""
    need_translation: bool
    need_year_conversion: bool
    country: str


class InstanceMetadata(BaseModel):
    """Metadata for a single exam/solution instance."""
    year: str
    exam_variant: str
    subject: str
    page_count: Optional[int] = None

    model_config = {"validate_assignment": True}


class InstanceDocuments(BaseModel):
    """Document paths for an instance."""
    exam_path: Optional[Union[Path, List[Path]]] = None
    solution_path: Optional[Union[Path, List[Path]]] = None


class Instance(BaseModel):
    """Complete instance containing config, metadata, and documents."""
    scraping_config: ScrapingConfig
    metadata: InstanceMetadata
    documents: InstanceDocuments

    @computed_field
    def year(self) -> str:
        return self.metadata.year

    @computed_field
    def exam_variant(self) -> str:
        return self.metadata.exam_variant

    @computed_field
    def subject(self) -> str:
        return self.metadata.subject

    @computed_field
    def page_count(self) -> Optional[int]:
        return self.metadata.page_count

    @computed_field
    def exam_document_path(self) -> Optional[Union[Path, List[Path]]]:
        return self.documents.exam_path

    @computed_field
    def solution_document_path(self) -> Optional[Union[Path, List[Path]]]:
        return self.documents.solution_path