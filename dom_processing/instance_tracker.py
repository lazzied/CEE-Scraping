from pathlib import Path
from supabase import Client
from dom_processing.my_scraper.models import Instance


class Tracker:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.visited_urls = []

    def check_entry_page_exists_in_exam_db(self, url: str) -> bool:
        """Check if entry_page_url already exists in exams table."""
        try:
            response = (
                self.supabase
                .table("exams")
                .select("exam_id")
                .eq("entry_page_url", url)
                .limit(1)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            raise e

    def get_exam_id_by_url(self, url: str) -> int | None:
        """Fetch the exam_id for a given entry_page_url."""
        try:
            response = (
                self.supabase
                .table("exams")
                .select("exam_id")
                .eq("entry_page_url", url)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]["exam_id"]
            return None
        except Exception as e:
            raise e

    def check_exam_file_exists_local_db(self, instance: Instance) -> bool:
        return instance.documents.exam_path.is_file()

    def check_solution_file_exists_local_db(self, instance: Instance) -> bool:
        
        return instance.documents.solution_path.is_file()

    def check_entry_page_exists_in_solution_db(self, url: str) -> bool:
        """Check if entry_page_url already exists in solution table."""
        try:
            response = (
                self.supabase
                .table("solution")
                .select("solution_id")
                .eq("entry_page_url", url)
                .limit(1)
                .execute()
            )
            return bool(response.data)
        except Exception as e:
            raise e

    def check_entry_page_exists_in_visited_urls(self, url: str) -> bool:
        return url in self.visited_urls

    def add_exam_entry_page_to_visited_urls(self, url: str) -> None:
        """Add newly inserted exam to cache to avoid re-scraping."""
        self.visited_urls.append(url)

    def add_solution_entry_page_to_visited_urls(self, url: str) -> None:
        self.visited_urls.append(url)