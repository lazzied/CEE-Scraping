from dataclasses import dataclass
from typing import Optional

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
    main_page_link: Optional[int]= None


@dataclass
class Solution:
    exam_id: Optional[int] = None
    local_path: Optional[str] = None
    solution_url: Optional[str] = None
    solution_id: Optional[int] = None
    main_page_link: Optional[int]= None

