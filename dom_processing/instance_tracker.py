from pathlib import Path
from typing import  Dict
from supabase import Client

from dom_processing.my_scraper.models import Instance

class Tracker:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.visited_urls=[]

    def check_entry_page_exists_in_exam_db(self, instance:Instance) -> bool:
        """Check if entry_page_url already exists in exams table."""
        try:
            response = (
                self.supabase
                .table("exams")
                .select("exam_id")
                .eq("entry_page_url", instance.documents.exam_entry_page_url)
                .limit(1)
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            raise e
    from pathlib import Path

    def check_exam_file_exists_local_db(self, instance: Instance, root_dir: Path) -> bool:
        if not isinstance(root_dir, Path):
            raise TypeError("root_dir must be a Path object")

        if not isinstance(instance.documents.exam_path, Path):
            raise TypeError("relative_path must be a Path object")

        full_path = root_dir / instance.documents.exam_path

        return full_path.is_file()
    
    def check_solution_file_exists_local_db(self, instance: Instance, root_dir: Path) -> bool:
        if not isinstance(root_dir, Path):
            raise TypeError("root_dir must be a Path object")

        if not isinstance(instance.documents.solution_path, Path):
            raise TypeError("relative_path must be a Path object")

        full_path = root_dir / instance.documents.solution_path

        return full_path.is_file()
        

    def check_entry_page_exists_in_solution_db(self,instance: Instance) -> bool:
        """Check if entry_page_url already exists in exams table."""
        try:
            response = (
                self.supabase
                .table("solution")
                .select("solution_id")
                .eq("entry_page_url", instance.documents.solution_entry_page_url)
                .limit(1)
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            raise e

    def check_entry_page_exists_in_visited_urls(self, url: str) -> bool:
        return url in self.visited_urls

    def add_exam_entry_page_to_visited_urls(self, instance: Instance) -> None:
        """Add newly inserted exam to cache to avoid re-scraping"""
        if instance.documents.exam_entry_page_url:  # Fixed attribute access
            self.visited_urls.append(instance.documents.exam_entry_page_url)  # Fixed self.self typo

    def add_solution_entry_page_to_visited_urls(self, instance: Instance) -> None:
        if instance.documents.solution_entry_page_url:  # Fixed attribute access
            self.visited_urls.append(instance.documents.solution_entry_page_url)  # Fixed self.self typo
