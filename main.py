import os
import sys
import traceback

# Suppress console output FIRST, before other imports
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')


from enum import Enum, auto

from my_data_structures.selenium_driver import SeleniumDriver
import json
from dom_processing.tree_builder import TreeBuilder
from dom_processing.scraper_versions.exam_solution_scraper import Scraper
from db.my_dataclasses import Exam, Solution
from utils import get_logger
from db.database_repo import DatabaseRepository
from db.database_prepare import DatabasePreparation
from supabase import create_client
from typing import Tuple, Optional
from dom_processing.instance_tracker import Tracker
from dotenv import load_dotenv
load_dotenv()

SCHEMA_FILES = {
    "main": "schemas/gaokao_v1.json",
    "document": "schemas/exam_pagev1.json",
    "config": "schemas/template_config.json"
}
MAIN_PAGE_URL = "https://gaokao.eol.cn/e_html/gk/gkst/"

def build_and_annotate_tree(seleniumdrv, schema):
    builder = TreeBuilder(seleniumdrv.driver, schema)
    builder.full_build_layout_tree()
    builder.annotate_regular_tree()

    return builder

class ScrapeStrategy(Enum):
    SKIP_ALL = auto()
    SCRAPE_SOLUTION_ONLY = auto()
    SCRAPE_SOLUTION_AND_EXAM = auto()

def decide_scrape_strategy(
        tracker: Tracker,
        metadata: dict
) -> ScrapeStrategy :
    exam_scraped , solution_scraped = tracker.is_instance_scraped(metadata)

    if exam_scraped and solution_scraped:
        return ScrapeStrategy.SKIP_ALL
    
    if exam_scraped and not solution_scraped:
        return ScrapeStrategy.SCRAPE_SOLUTION_ONLY
    
    return ScrapeStrategy.SCRAPE_SOLUTION_AND_EXAM



def scrape_exam(scraper, drv, exam: Exam):
    logger = get_logger("scrape_exam_")
    try:
        logger.info(f"Starting exam scrape: {exam.exam_url}")
        scraper.scraper_orchestrator()
        logger.info(f"Completed exam scrape: {exam.subject}")
        drv.close()
        return exam  # Return populated exam
        
    except Exception as e:
        logger.error(f"Error scraping exam: {e}")
        logger.error(traceback.format_exc())
        return exam


def scrape_solution( document_schema, solution: Solution):
    # Create thread-specific logger
    logger = get_logger(f"scrape_solution_")
    
    try:
        logger.info(f"Starting solution scrape: {solution.solution_url}")
        
        drv = load_link(solution.solution_url)
        builder = build_and_annotate_tree(drv, document_schema)
        scraper = Scraper(drv.driver, builder.root_node, "Solution", solution)
        scraper.scraper_orchestrator()
        
        logger.info(f"Completed solution scrape")
        
        drv.close()
        return solution  # Return populated solution
        
    except Exception as e:
        logger.error(f"Error scraping solution: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return solution

def initialize_supabase():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    return supabase

def load_schemas():
    """Load all JSON schemas"""
    schemas = {}
    for name, path in SCHEMA_FILES.items():
        with open(path) as f:
            schemas[name] = json.load(f)
    return schemas

def load_link(link:str):
    driver = SeleniumDriver(headless=True)
    driver.get(link)
    return driver



def extract_exam_and_solution_links(subj, logger):
    """
    Extracts exam and solution URLs from a subject node.
    
    Args:
        subj: The subject node containing <a> tags.
        logger: Logger instance for logging messages.
    
    Returns:
        Tuple[str, Optional[str]]: (exam_url, solution_url)
        Returns (None, None) if no valid exam link is found.
    """
    
    def is_valid_url(url: str) -> bool:
        """Check if a URL is non-empty and starts with http."""
        return bool(url and url.strip() and url.startswith("http"))
    
    links = subj.find_in_node("tag", "a", find_all=True)
    logger.info(f"Found {len(links)} links")
    
    if not links:
        logger.warning("No links found in subject, skipping")
        return None, None
    
    # --- Process Exam Link ---
    exam_link = links[0].web_element
    exam_url = exam_link.get_attribute("href")
    exam_text = exam_link.text or "Unknown"
    
    if not is_valid_url(exam_url):
        logger.warning(f"Invalid exam URL for '{exam_text}', skipping subject")
        return None, None
    
    logger.info(f"Exam link: {exam_text} -> {exam_url}")
    
    # --- Process Solution Link (Optional) ---
    solution_url = None
    if len(links) > 1:
        solution_link = links[1].web_element
        solution_url_candidate = solution_link.get_attribute("href")
        solution_text = solution_link.text or "Unknown"
        
        if is_valid_url(solution_url_candidate):
            solution_url = solution_url_candidate
            logger.info(f"Solution link: {solution_text} -> {solution_url}")
        else:
            logger.warning(f"Invalid solution URL: {solution_url_candidate}, skipping solution")
    
    return exam_url, solution_url

def create_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def create_exam_and_solution(
    exam_url: str,
    solution_url: Optional[str],
    main_page_link: str
) -> Tuple["Exam", Optional["Solution"]]:
   
    # --- Create Exam instance ---
    exam = Exam(
        country="china",
        exam_url=exam_url,
        main_page_link=main_page_link
    )
    
    # --- Create Solution instance if available ---
    solution = None
    if solution_url:
        exam.solution_exist = True
        solution = Solution(
            solution_url=solution_url,
            main_page_link=main_page_link
        )
    
    return exam, solution   


def main():
    logger = get_logger("main")

    supabase = initialize_supabase()
    tracker = Tracker(MAIN_PAGE_URL, supabase)  # Changed from "SAVE_PATH"
    tracker.set_database_instances()
    db_repo = DatabaseRepository(supabase)
    db_prep = DatabasePreparation()
    
    schemas = load_schemas()
    main_driver = load_link(MAIN_PAGE_URL)
    main_builder = TreeBuilder(main_driver.driver, schemas["main"], schemas["config"])
    main_builder.full_build_layout_tree()

    logger.info(main_builder.root_node.get_dom_tree_str())

    exam_variant_nodes = main_builder.root_node.find_in_node("class", "test",  find_all=True )
    logger.info(f"Found {len(exam_variant_nodes)} exam variant nodes")
    i =1

    for exam_variant_node in exam_variant_nodes:
        logger.info(f"loop num; {i}")
        i+=1
        try:
            # error: it keeps looping in the same exam_variant:
            # all the exam variant nodes are the same: the first element yes this is the case; i need to test the annotate sti branch alone
            # endless inside loop

            
            # Annotate the branch
            drv = load_link(MAIN_PAGE_URL)

            builder = TreeBuilder(drv.driver, schemas["main"], schemas["config"], root_node =main_builder.root_node )
            builder.annotate_sti_branch(exam_variant_node)
            #logger.debug(exam_variant_node.web_element.id)

            logger.info(f" this is the exam_variant_node structure {exam_variant_node.get_dom_tree_str()}")
            subjects = exam_variant_node.find_in_node("tag", "li", find_all=True)
            
            # Process each subject
            logger.info(f"this is the length of subject list: {len(subjects)}")
            for subj in reversed(subjects):
                try:
                    exam_url, solution_url = extract_exam_and_solution_links(subj, logger)

                    if not exam_url:
                        continue

                    logger.info(f"Processing exam: {exam_url}")
                    
                    exam, solution = create_exam_and_solution(
                        exam_url,
                        solution_url,
                        MAIN_PAGE_URL
                    )

                    drv = load_link(exam.exam_url)
                    builder = build_and_annotate_tree(drv, schemas["document"])
                    scraper = Scraper(drv.driver, builder.root_node, "Exam", exam)

                    instance_metadata = scraper.get_metadata()

                    strategy = decide_scrape_strategy(tracker, instance_metadata)
                    
                    if strategy == ScrapeStrategy.SKIP_ALL:
                        logger.info(f"Skipping exam and solution already scraped: {instance_metadata}")
                        drv.close()  # Close the driver we just opened
                        continue
                        
                    if strategy == ScrapeStrategy.SCRAPE_SOLUTION_ONLY:
                        drv.close()  # Close exam driver since we don't need it
                        solution = scrape_solution(schemas["document"], solution)
                        relative_exam_id = tracker.get_exam_id(instance_metadata)
                        solution_dict = db_prep.prepare_solution_for_database(solution)
                        solution_id = db_repo.insert_solution(solution_dict, relative_exam_id)
                        tracker.add_solution_to_cache(solution_id, relative_exam_id)
                        logger.info(f"Inserted solution with ID: {solution_id}")
                        
                    elif strategy == ScrapeStrategy.SCRAPE_SOLUTION_AND_EXAM:
                        exam = scrape_exam(scraper, drv, exam)  # This closes drv
                        solution = scrape_solution(schemas["document"], solution)
                        solution_dict = db_prep.prepare_solution_for_database(solution)
                        exam_dict = db_prep.prepare_exam_for_database(exam)
                        exam_id, solution_id = db_repo.insert_exam_with_solution(exam_dict, solution_dict)
                        tracker.add_exam_to_cache(exam_dict, exam_id)
                        tracker.add_solution_to_cache(solution_id, exam_id)  
                        logger.info(f"Inserted exam {exam_id} and solution {solution_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing subject: {e}")
                    logger.error(traceback.format_exc())
                    # Make sure to close driver if it was opened
                    try:
                        if 'drv' in locals():
                            drv.close()
                    except:
                        pass
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing exam variant node: {e}")
            logger.error(traceback.format_exc())
            continue
    
    main_driver.close()
    logger.info("Main process completed")


if __name__ == "__main__":
    main()