from typing import Optional, Tuple, List
from my_dataclasses import Exam, Solution, DocumentLink
from test_functions import get_logger

class DatabasePreparation:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def prepare_for_database(
        self, 
        exam: Exam, 
        solution: Optional[Solution] = None
    ) -> Tuple[dict, Optional[dict], List[dict]]:
        """
        Transform dataclasses into database-ready dictionaries with proper relationships.
    
        Returns:
            (exam_dict, solution_dict, document_links_list)
        """
        self.logger.info("Preparing data for database insertion")
        
        # Step 1: Prepare Exam (will get exam_id from database after insert)
        exam_dict = self._prepare_exam(exam)
        
        # Step 2: Prepare Solution if exists
        solution_dict = None
        if solution and exam.solution_exist:
            solution_dict = self._prepare_solution(solution)
            exam_dict["solution_exist"] = True
        else:
            exam_dict["solution_exist"] = False
        
        # Step 3: Prepare DocumentLinks (exam + solution)
        document_links = self._prepare_document_links(exam, solution)
        
        self.logger.info(f"Prepared exam, solution={solution is not None}, links={len(document_links)}")
        
        return exam_dict, solution_dict, document_links

    
    def _prepare_exam(self, exam: Exam) -> dict:
        """Prepare exam dict without ID (database will auto-increment)"""
        exam_dict = {
            "country": exam.country,
            "province": exam.province,
            "subject": exam.subject,
            "year": exam.year,
            "exam_variant": exam.exam_variant,
            "exam_url": exam.exam_url,
            "local_path": exam.local_path,
            "solution_exist": exam.solution_exist or False,
        }
        
        self.logger.info(f"Exam dict: {exam_dict}")
        return exam_dict
 
    
    def _prepare_solution(self, solution: Solution) -> dict:
        """Prepare solution dict without IDs (will be set later)"""
        return {
            "local_path": solution.local_path,
            "solution_url": solution.solution_url,
            # solution_id will be assigned by database
            # exam_id will be set after exam insert
        }
    
    def _prepare_document_links(self, exam: Exam, solution: Optional[Solution]) -> List[dict]:
        """Prepare all document links from both exam and solution"""
        links = []
        
        self.logger.info(f"Exam downloaded_links: {exam.downloaded_links}")
        if solution:
            self.logger.info(f"Solution downloaded_links: {solution.downloaded_links}")
        
        # Add exam document links
        if exam.downloaded_links:
            for link in exam.downloaded_links:
                links.append({
                    "document_state": "Exam",
                    "page_number": link.page_number,
                    "link": link.link,
                })
        else:
            self.logger.warning("Exam has no downloaded_links!")
        
        # Add solution document links
        if solution and solution.downloaded_links:
            for link in solution.downloaded_links:
                links.append({
                    "document_state": "Solution",
                    "page_number": link.page_number,
                    "link": link.link,
                })
        
        self.logger.info(f"Total document links prepared: {len(links)}")
        return links

        