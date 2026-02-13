from db.my_dataclasses import Exam, Solution
from utils import get_logger
from dom_processing.chinese_to_english_dictionnary import translate_to_english
class DatabasePreparation:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def prepare_exam_for_database(self, exam: Exam) -> dict:
        
        self.logger.info("Preparing exam for database insertion")
        
        exam_dict = {
            "country": exam.country,
            "province": exam.province,
            "subject": exam.subject,
            "year": exam.year,
            "exam_variant": exam.exam_variant,
            "exam_url": exam.exam_url,
            "local_path": exam.local_path,
            "solution_exist": exam.solution_exist or False,
            "exam_variant_en": translate_to_english[exam.exam_variant] ,
            "subject_en": translate_to_english[exam.subject],
            "main_page_link": exam.main_page_link

        }
        
        self.logger.info(f"Exam dict prepared: {exam_dict}")
        return exam_dict
    
    def prepare_solution_for_database(self, solution: Solution) -> dict:
        
        self.logger.info("Preparing solution for database insertion")
        
        solution_dict = {
            "local_path": solution.local_path,
            "solution_url": solution.solution_url,
            "main_page_link": solution.main_page_link

            # exam_id will be set by caller before insert
        }
        
        self.logger.info(f"Solution dict prepared: {solution_dict}")
        return solution_dict