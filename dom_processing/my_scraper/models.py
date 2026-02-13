"""
Data models and enums for the scraping system.
"""

from pathlib import Path
from typing import Union, Optional, List
from pydantic import BaseModel, Field, computed_field


class InstanceMetadata(BaseModel):
    year: Optional[str] = None
    exam_variant: Optional[list[str]] = None
    subject: Optional[str] = None



class InstanceDocuments(BaseModel):
    exam_path: Optional[Path] = None
    exam_url: Optional[str] = None
    solution_path: Optional[Path] = None
    solution_url: Optional[str] = None


class Instance(BaseModel):
    metadata: InstanceMetadata = Field(default_factory=InstanceMetadata)
    documents: InstanceDocuments = Field(default_factory=InstanceDocuments)

    @computed_field
    def year(self) -> str:
        return self.metadata.year

    @computed_field
    def exam_variant(self) -> list[str]:
        return self.metadata.exam_variant

    @computed_field
    def subject(self) -> str:
        return self.metadata.subject

    @computed_field
    def exam_document_path(self) -> Optional[Path]:
        return self.documents.exam_path

    @computed_field
    def solution_document_path(self) -> Optional[Path]:
        return self.documents.solution_path
