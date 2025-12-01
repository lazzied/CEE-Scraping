from supabase import Client
from test_functions import get_logger
from typing import Optional, List, Tuple

class DatabaseRepository:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
        self.logger = get_logger(__name__)
    
    def insert_exam_with_relations(
        self,
        exam_dict: dict,
        solution_dict: Optional[dict],
        document_links: List[dict]
    ) -> Tuple[int, Optional[int]]:
        """
        Insert exam, solution, and document links with proper foreign key relationships.
        
        Returns:
            (exam_id, solution_id)
        """
        try:
            # Step 1: Insert Exam (get auto-incremented exam_id)
            exam_response = self.supabase.table("exams").insert(exam_dict).execute()
            exam_id = exam_response.data[0]["exam_id"]
            self.logger.info(f"Inserted exam with ID: {exam_id}")

            
            # Step 2: Insert Solution if exists (get solution_id)
            solution_id = None
            if solution_dict:
                solution_dict["exam_id"] = exam_id  # Set foreign key
                solution_response = self.supabase.table("solutions").insert(solution_dict).execute()
                solution_id = solution_response.data[0]["solution_id"]
                self.logger.info(f"Inserted solution with ID: {solution_id}")
                
                # Update exam with solution_id
                self.supabase.table("exams").update({
                    "solution_id": solution_id,
                    "solution_exist": True
                }).eq("exam_id", exam_id).execute()
                self.logger.info(f"Updated exam {exam_id} with solution_id {solution_id}")
                """
                sql equivalent
                UPDATE exams
                SET solution_id = <value>, solution_exist = TRUE
                WHERE exam_id = <some id>;
                """
            
            # Step 3: Insert Document Links with proper document_id (foreign key)
            for link in document_links:
                if link["document_state"] == "Exam":
                    link["document_id"] = exam_id  # Foreign key to exam
                elif link["document_state"] == "Solution":
                    link["document_id"] = solution_id  # Foreign key to solution
                
                self.supabase.table("document_links").insert(link).execute()
            
            self.logger.info(f"Inserted {len(document_links)} document links")
            
            return exam_id, solution_id
            
        except Exception as e:
            self.logger.error(f"Database insertion error: {e}")
            raise
    
    def batch_insert_exam_with_relations(
        self,
        prepared_data_list: List[Tuple[dict, Optional[dict], List[dict]]]
    ):
        """Insert multiple exams with their relations"""
        for exam_dict, solution_dict, document_links in prepared_data_list:
            self.insert_exam_with_relations(exam_dict, solution_dict, document_links)