from typing import List, Dict, Tuple
from supabase import Client
from utils import get_logger

class Tracker:
    def __init__(self, main_page_link: str, supabase: Client):
        self.main_page_link = main_page_link
        self.supabase = supabase
        self.exam_rows: List[Dict] = []
        self.solution_rows: List[Dict] = []


        self.logger = get_logger(__name__)




    def set_database_instances(self) -> None:
        """Fetch and cache all database instances"""
        self.exam_rows = (
            self.supabase
            .table("exams")
            .select("exam_id, exam_variant, subject, solution_exist")
            .eq("main_page_link", self.main_page_link)
            .execute()
            .data
        )
        self.logger.info(f"fetched the current exams database {self.exam_rows}")

        self.solution_rows = (
            self.supabase
            .table("solutions")
            .select("solution_id, exam_id")
            .eq("main_page_link", self.main_page_link)
            .execute()
            .data
        )
        self.logger.info(f"fetched the current exams database {self.solution_rows}")


    def add_exam_to_cache(self, exam_dict: Dict, exam_id: int) -> None:
        """Add newly inserted exam to cache to avoid re-scraping"""
        self.exam_rows.append({
            "exam_id": exam_id,
            "exam_variant": exam_dict["exam_variant"],
            "subject": exam_dict["subject"],
            "solution_exist": exam_dict.get("solution_exist", False)
        })
        self.logger.info(f"added exam to cache {exam_dict}")

    def add_solution_to_cache(self, solution_id: int, exam_id: int) -> None:
        """Add newly inserted solution to cache"""
        self.solution_rows.append({
            "solution_id": solution_id,
            "exam_id": exam_id
        })

        self.logger.info(f"added solution to cache, solution id: {solution_id}, exam_id{exam_id}")

    def get_exam_id(self, instance: Dict) -> int:
        """Get exam_id for a given instance metadata."""
        exam_row = next(
            (
                row for row in self.exam_rows
                if row["exam_variant"] == instance["exam_variant"]
                and row["subject"] == instance["subject"]
            ),
            None
        )

        if not exam_row:
            raise ValueError(
                f"No exam found for variant '{instance['exam_variant']}' "
                f"and subject '{instance['subject']}'"
            )

        return exam_row["exam_id"]

    def is_instance_scraped(self, instance: Dict) -> Tuple[bool, bool]:
        """
        Returns: (exam_scraped, solution_scraped)
        """
        exam_variant = instance["exam_variant"]
        subject = instance["subject"]

        exam_row = next(
            (
                row for row in self.exam_rows
                if row["exam_variant"] == exam_variant
                and row["subject"] == subject
            ),
            None
        )

        if not exam_row:
            return False, False

        exam_scraped = True

        # Check if solution is expected
        solution_expected = exam_row["solution_exist"]
        if solution_expected in (False, "FALSE", None, "", 0):
            return exam_scraped, True # this means solution doesn't exist that why we return TRUE

        # Check if solution exists
        exam_id = exam_row["exam_id"]
        solution_scraped = any(
            sol["exam_id"] == exam_id
            for sol in self.solution_rows
        )

        return exam_scraped, solution_scraped