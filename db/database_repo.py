from datetime import datetime
from supabase import Client
from db.database_models import ExamRecord, SolutionRecord
from dataclasses import asdict


class DatabaseRepository:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    def insert_exam_record(self, exam_record: ExamRecord) -> int:
        """Insert exam record into database."""
        try:
            # Convert dataclass to dict, remove None and exam_id
            exam_dict = {k: v for k, v in asdict(exam_record).items() 
                        if v is not None and k != 'exam_id'}
            
            for key, value in exam_dict.items():
                if isinstance(value, datetime):
                    exam_dict[key] = value.isoformat()
                
            response = self.supabase.table("exams").insert(exam_dict).execute()
            exam_id = response.data[0]["exam_id"]
            return exam_id
            
        except Exception as e:
            raise
    
    def insert_solution_record(self, solution_record: SolutionRecord, exam_id: int) -> int:
        """Insert solution record into database."""
        try:
            solution_dict = {k: v for k, v in asdict(solution_record).items() 
                           if v is not None and k not in ['solution_id', 'exam_id']}
            solution_dict["exam_id"] = exam_id

            for key, value in solution_dict.items():
                if isinstance(value, datetime):
                    solution_dict[key] = value.isoformat()
            
            response = self.supabase.table("solutions").insert(solution_dict).execute()
            solution_id = response.data[0]["solution_id"]
            
            # Update exam with solution_id
            self.supabase.table("exams").update({
                "solution_id": solution_id,
                "solution_exists": True
            }).eq("exam_id", exam_id).execute()
            
            return solution_id
            
        except Exception as e:
            raise
