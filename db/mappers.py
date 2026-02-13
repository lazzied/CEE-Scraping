# ============================================================================
# mappers.py - Transform between domain and database models
# ============================================================================

from datetime import datetime
from typing import List, Tuple, Optional
from db.database_models import ExamRecord, SolutionRecord
from dom_processing.my_scraper.interfaces_implementations import ChineseContentTransformer
from dom_processing.my_scraper.models import Instance


class InstanceToRecordMapper:
    """Maps scraper Instance to database records."""
    
    def __init__(self, translator: ChineseContentTransformer = None):
        self.translator = translator or ChineseContentTransformer()

        
    def map_to_multiple_exam_records(self, instance: Instance) -> List[ExamRecord]:
        """Convert Instance to multiple ExamRecords (one per exam_variant)."""

        exam_records: List[ExamRecord] = []

        # If no variants, create one record with None
        variants = instance.exam_variant or [None]

        for variant in variants:

            exam_records.append(
                ExamRecord(
                    # Location
                    country=instance.country,
                    language=instance.language,
                    province=instance.province,

                    # Metadata
                    subject=instance.subject,
                    subject_en=self.translator.translate_to_english(instance.subject)
                    if instance.subject else None,

                    exam_variant=variant,
                    exam_variant_en=self.translator.translate_to_english(variant)
                    if variant else None,

                    year=int(instance.year) if instance.year else None,

                    # URLs and paths
                    exam_url=instance.documents.exam_url,
                    local_path=str(instance.documents.exam_path)
                    if instance.documents.exam_path else None,
                    entry_page_link=instance.documents.exam_entry_page_link,

                    # File metadata
                    file_format=instance.file_format,
                    page_count=instance.documents.exam_page_count,

                    # Solution relationship
                    solution_exist=instance.solution_exists,

                    # Scraping metadata
                    scraped_at=instance.scraped_at or datetime.now(),
                    scraping_status=instance.scraping_status or "success",
                    error_message=instance.error_message
                )
            )

        return exam_records

    def map_to_single_exam_record(self, instance: Instance) -> ExamRecord:
        """Convert Instance to ExamRecord."""
        
        return ExamRecord(
            # Location
            country=instance.country,
            language=instance.language,
            province=instance.province,
            
            # Metadata
            subject=instance.subject,
            subject_en=self.translator.translate_to_english(instance.subject) if instance.subject else None,
            exam_variant=instance.exam_variant,
            exam_variant_en=self.translator.translate_to_english(instance.exam_variant) if instance.exam_variant else None,
            year=int(instance.year) if instance.year else None,
            
            # URLs and paths
            exam_url=instance.documents.exam_url,
            local_path=str(instance.documents.exam_path) if instance.documents.exam_path else None,
            entry_page_link=instance.documents.exam_entry_page_link,
            
            # File metadata
            file_format=instance.file_format,
            page_count=instance.documents.exam_page_count,
            
            # Solution relationship
            solution_exist=instance.solution_exists,
            
            # Scraping metadata
            scraped_at=instance.scraped_at or datetime.now(),
            scraping_status=instance.scraping_status or "success",
            error_message=instance.error_message
        )
    
    def map_to_solution_record(self, instance: Instance) -> Optional[SolutionRecord]:
        """Convert Instance to SolutionRecord (if solution exists)."""
        
        if not instance.solution_exists:
            return None
        
        return SolutionRecord(
            # URLs and paths
            solution_url=instance.documents.solution_url,
            local_path=str(instance.documents.solution_path) if instance.documents.solution_path else None,
            entry_page_link=instance.documents.solution_entry_page_link,
            
            # File metadata
            file_format=instance.file_format,
            page_count=instance.documents.solution_page_count,
            
            # Scraping metadata
            scraped_at=instance.scraped_at or datetime.now(),
            scraping_status=instance.scraping_status or "success",
            error_message=instance.error_message
        )
    
    