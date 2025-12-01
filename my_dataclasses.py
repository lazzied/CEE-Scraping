from dataclasses import dataclass
from typing import Optional, List


@dataclass
class DocumentLink:
    document_state: Optional[str] = None   # "Exam" or "Solution"
    page_number: Optional[int] = None
    link: Optional[str] = None
    document_id: Optional[int] = None


@dataclass
class Exam:
    country: Optional[str] = None
    province: Optional[str] = None
    subject: Optional[str] = None
    year: Optional[int] = None
    exam_variant: Optional[str] = None
    exam_url: Optional[str] = None
    local_path: Optional[str] = None
    solution_exist: Optional[bool] = None
    solution_id: Optional[int] = None
    exam_id: Optional[int] = None
    downloaded_links: Optional[List[DocumentLink]] = None   


@dataclass
class Solution:
    exam_id: Optional[int] = None
    local_path: Optional[str] = None
    solution_url: Optional[str] = None
    solution_id: Optional[int] = None
    downloaded_links: Optional[List[DocumentLink]] = None   #
