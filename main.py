import os
import sys
import traceback

# Suppress console output FIRST, before other imports
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

from selenium_driver import SeleniumDriver
import json, threading
from tree_builder import TreeBuilder
from exam_solution_scraper import Scraper
from my_dataclasses import Exam, Solution
from test_functions import get_logger
from checkpoint_manager import CheckpointManager
from database_repo import DatabaseRepository
from database_prepare import DatabasePreparation
from supabase import create_client
from selenium.common.exceptions import NoSuchElementException
from test_functions import load_translation_map

from dotenv import load_dotenv

load_dotenv()
translation_map = load_translation_map()

def scrape_exam(exam_url, document_schema, backup_schema, exam: Exam, 
                checkpoint: CheckpointManager):
    """Scrape exam with automatic backup schema fallback."""
    logger = get_logger(f"scrape_exam_{threading.current_thread().name}")
    
    try:
        logger.info(f"Starting exam scrape: {exam_url}")
        
        drv = SeleniumDriver(headless=True)
        drv.get(exam_url)
        
        # Check if this URL previously failed with main schema
        failed_schema = checkpoint.get_failed_schema(exam_url)
        if failed_schema == "main":
            logger.info(f"Using backup schema for {exam_url} (main schema failed previously)")
            schema_to_use = backup_schema
            schema_name = "backup"
        else:
            schema_to_use = document_schema
            schema_name = "main"
        
        builder = TreeBuilder(drv.driver, schema_to_use)
        
        try:
            builder.full_build_layout_tree()
            builder.annotate_regular_tree()
        except NoSuchElementException as e:
            logger.warning(f"Schema '{schema_name}' failed: {e}")
            
            # Try backup schema if main failed
            if schema_name == "main" and backup_schema:
                logger.info("Attempting backup schema...")
                checkpoint.record_schema_failure(exam_url, "main")
                
                # Rebuild with backup schema
                builder = TreeBuilder(drv.driver, backup_schema)
                builder.full_build_layout_tree()
                builder.annotate_regular_tree()
                logger.info("Backup schema successful")
            else:
                raise  # No backup available or backup also failed
        
        scraper = Scraper(drv.driver, builder.root_node, "Exam", exam,translation_map)
        scraper.scraper_orchestrator()
        
        logger.info(f"Completed exam scrape: {exam.subject}")
        drv.close()
        return exam
        
    except Exception as e:
        logger.error(f"Error scraping exam: {e}")
        logger.error(traceback.format_exc())
        if 'drv' in locals():
            drv.close()
        return exam


def scrape_solution(solution_url, document_schema, backup_schema, 
                   solution: Solution, checkpoint: CheckpointManager):
    """Scrape solution with automatic backup schema fallback."""
    logger = get_logger(f"scrape_solution_{threading.current_thread().name}")
    
    try:
        logger.info(f"Starting solution scrape: {solution_url}")
        
        drv = SeleniumDriver(headless=True)
        drv.get(solution_url)
        
        # Check if this URL previously failed with main schema
        failed_schema = checkpoint.get_failed_schema(solution_url)
        if failed_schema == "main":
            logger.info(f"Using backup schema for {solution_url} (main schema failed previously)")
            schema_to_use = backup_schema
            schema_name = "backup"
        else:
            schema_to_use = document_schema
            schema_name = "main"
        
        builder = TreeBuilder(drv.driver, schema_to_use)
        
        try:
            builder.full_build_layout_tree()
            builder.annotate_regular_tree()
        except NoSuchElementException as e:
            logger.warning(f"Schema '{schema_name}' failed: {e}")
            
            # Try backup schema if main failed
            if schema_name == "main" and backup_schema:
                logger.info("Attempting backup schema...")
                checkpoint.record_schema_failure(solution_url, "main")
                
                # Rebuild with backup schema
                builder = TreeBuilder(drv.driver, backup_schema)
                builder.full_build_layout_tree()
                builder.annotate_regular_tree()
                logger.info("Backup schema successful")
            else:
                raise  # No backup available or backup also failed
        
        scraper = Scraper(drv.driver, builder.root_node, "Solution", solution,translation_map)
        scraper.scraper_orchestrator()
        
        logger.info(f"Completed solution scrape")
        drv.close()
        return solution
        
    except Exception as e:
        logger.error(f"Error scraping solution: {e}")
        logger.error(traceback.format_exc())
        if 'drv' in locals():
            drv.close()
        return solution


def main():
    logger = get_logger("main")
    checkpoint = CheckpointManager()
    
    logger.info(checkpoint.get_resume_info())
    
    # Initialize database
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    db_repo = DatabaseRepository(supabase)
    db_prep = DatabasePreparation()
    
    # Load schemas (including backup)
    with open("schemas/gaokao_v1.json") as f:
        main_schema = json.load(f)
    with open("schemas/exam_pagev1.json") as f:
        document_schema = json.load(f)
    with open("schemas/exam_pagev2.json") as f:
        backup_document_schema = json.load(f)
    with open("schemas/template_config.json") as f:
        config = json.load(f)
    
    # Build main page tree
    main_driver = SeleniumDriver(headless=True)
    main_driver.get("https://gaokao.eol.cn/e_html/gk/gkst/")
    main_builder = TreeBuilder(main_driver.driver, main_schema, config)
    main_builder.full_build_layout_tree()
    
    exam_variant_nodes = main_builder.root_node.find_in_node(
        "class", "test", find_all=True
    )
    
    
    # CHECKPOINT LOOP 1: Iterate through variants
    for variant_idx, exam_variant_node in enumerate(exam_variant_nodes):
        logger.info(f"Processing variant {variant_idx}/{len(exam_variant_nodes)}")
        
        main_builder.annotate_sti_branch(exam_variant_node)
        subjects = exam_variant_node.find_in_node("tag", "li", find_all=True)
        
        # CHECKPOINT LOOP 2: Iterate through subjects
        for subject_idx, subj in enumerate(subjects):
            try:
                links = subj.find_in_node("tag", "a", find_all=True)
                
                if not links or len(links) == 0:
                    logger.warning("No links found in subject, skipping")
                    continue
                
                exam_url = links[0].web_element.get_attribute("href")
                exam_text = links[0].web_element.text or "Unknown"
                
                if not exam_url or exam_url.strip() == "":
                    logger.warning(f"Exam link is empty for '{exam_text}', skipping")
                    continue
                
                if not exam_url.startswith("http"):
                    logger.warning(f"Invalid exam URL format: {exam_url}, skipping")
                    continue
                
                # CHECK CHECKPOINT: Skip if already processed
                if checkpoint.should_skip(variant_idx, subject_idx, exam_url):
                    logger.info(f"Skipping already processed: {exam_url}")
                    continue
                
                logger.info(f"Exam link: {exam_text} -> {exam_url}")
                
                # Get solution URL
                solution_url = None
                if len(links) > 1:
                    solution_url = links[1].web_element.get_attribute("href")
                    if solution_url and (solution_url.strip() == "" or 
                                        not solution_url.startswith("http")):
                        solution_url = None
                
                # Create dataclass instances
                
                exam = Exam(country="china", exam_url=exam_url)
                
                solution = None
                if solution_url:
                    exam.solution_exist = True
                    solution = Solution( 
                                       solution_url=solution_url)
                
                # Launch threads with backup schema support
                threads = []
                results = {}
                
                def exam_wrapper():
                    results['exam'] = scrape_exam(
                        exam_url, document_schema, backup_document_schema,
                         exam, checkpoint
                    )
                
                def solution_wrapper():
                    results['solution'] = scrape_solution(
                        solution_url, document_schema, backup_document_schema,
                         solution, checkpoint
                    )
                
                t1 = threading.Thread(target=exam_wrapper, 
                                     name=f"exam_{exam.subject or 'unknown'}")
                t1.start()
                threads.append(t1)
                
                if solution_url:
                    t2 = threading.Thread(target=solution_wrapper, 
                                         name=f"solution_{exam.subject or 'unknown'}")
                    t2.start()
                    threads.append(t2)
                
                for t in threads:
                    t.join()
                
                logger.info("Threads completed, preparing database insertion")
                
                # Prepare and insert into database
                exam_dict, solution_dict, document_links = db_prep.prepare_for_database(
                    results.get('exam', exam),
                    results.get('solution', solution)
                )
                
                try:
                    exam_id, solution_id = db_repo.insert_exam_with_relations(
                        exam_dict, solution_dict, document_links
                    )
                    logger.info(f"Successfully inserted exam_id={exam_id}, "
                               f"solution_id={solution_id}")
                    
                    # SAVE CHECKPOINT after successful completion
                    checkpoint.save_checkpoint(variant_idx, subject_idx, exam_url)
                    logger.info(f"Checkpoint saved: variant={variant_idx}, "
                               f"subject={subject_idx}")
                    
                except Exception as e:
                    logger.error(f"Failed to insert into database: {e}")
                    logger.error(traceback.format_exc())
                    # Don't save checkpoint on DB failure - retry next run
                    
            except Exception as e:
                logger.error(f"Error processing subject at variant={variant_idx}, "
                           f"subject={subject_idx}: {e}")
                logger.error(traceback.format_exc())
                continue
    
    main_driver.close()
    logger.info("Main process completed successfully")
    
    # Optionally reset checkpoint after full completion
    # checkpoint.reset()


if __name__ == "__main__":
    main()