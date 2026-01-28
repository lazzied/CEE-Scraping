from supabase import Client
from utils import get_logger
from typing import Optional, Tuple

class DatabaseRepository:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.logger = get_logger(__name__)
    
    def insert_exam(self, exam_dict: dict) -> int:
        """
        Insert exam into database.
        
        Returns:
            exam_id
        """
        try:
            exam_response = self.supabase.table("exams").insert(exam_dict).execute()
            exam_id = exam_response.data[0]["exam_id"]
            self.logger.info(f"Inserted exam with ID: {exam_id}")
            return exam_id
            
        except Exception as e:
            self.logger.error(f"Exam insertion error: {e}")
            raise
    
    def insert_solution(self, solution_dict: dict, exam_id: int) -> int:
        """
        Insert solution into database with exam foreign key.
        
        Returns:
            solution_id
        """
        try:
            # Set foreign key
            solution_dict["exam_id"] = exam_id
            
            # Insert solution
            solution_response = self.supabase.table("solutions").insert(solution_dict).execute()
            solution_id = solution_response.data[0]["solution_id"]
            self.logger.info(f"Inserted solution with ID: {solution_id}")
            
            # Update exam with solution_id
            self.supabase.table("exams").update({
                "solution_id": solution_id,
                "solution_exist": True
            }).eq("exam_id", exam_id).execute()
            self.logger.info(f"Updated exam {exam_id} with solution_id {solution_id}")
            
            return solution_id
            
        except Exception as e:
            self.logger.error(f"Solution insertion error: {e}")
            raise
    
    def insert_exam_with_solution(self, exam_dict: dict, solution_dict: Optional[dict]) -> Tuple[int, Optional[int]]:
        """
        Insert exam and solution together.
        
        Returns:
            (exam_id, solution_id)
        """
        try:
            # Insert exam first
            exam_id = self.insert_exam(exam_dict)
            
            # Insert solution if exists
            solution_id = None
            if solution_dict:
                solution_id = self.insert_solution(solution_dict, exam_id)
            
            return exam_id, solution_id
            
        except Exception as e:
            self.logger.error(f"Database insertion error: {e}")
            raise
