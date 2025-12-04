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
from database_repo import DatabaseRepository
from database_prepare import DatabasePreparation
from supabase import create_client

from dotenv import load_dotenv
load_dotenv()
"""
features to develop:
    - merge with main
    - create a new branch named optimize looping
    - create a faulty html test subject to test all of the new features below
    - isolate components, just for testing, see how
    - fix get sibling method in node
    - write a logger for a faulty node
    - write a previous state text object, no need to redo the loop from the beginning, only from where the (exam/solution) pair 
    - add the fallback json schema in  case of a faulty node: this can be detected in the annotation phase or the building phase, so i need to add it to both
    - add the list of all links years
    - organize better folder structure: CEE/DOCUEMNTS/(YEAR)/(EXAM VARIANT)/(SUBJECT)/(SOLUTION OR EXAM)
    - add json schemas for the older years, they don't follow the same html structure
    - implement the schema switch mechanism
    - Document the entire process, add comments, write a latex file on it, diagrams all of this to be able to scale the app later on, turn all the hardcodedd methods to general ones
    - write a plan for the latex converter
    """

def scrape_exam(exam_url, document_schema, save_path, exam: Exam):
    # Create thread-specific logger
    logger = get_logger(f"scrape_exam_{threading.current_thread().name}")
    
    try:
        logger.info(f"Starting exam scrape: {exam_url}")
        
        drv = SeleniumDriver(headless=True)
        drv.get(exam_url)

        builder = TreeBuilder(drv.driver, document_schema)
        builder.full_build_layout_tree()
        builder.annotate_regular_tree()
        
        scraper = Scraper(drv.driver, builder.root_node, "Exam", save_path, exam)
        scraper.scraper_orchestrator()
        
        logger.info(f"Completed exam scrape: {exam.subject}")
        
        drv.close()
        return exam  # Return populated exam
        
    except Exception as e:
        logger.error(f"Error scraping exam: {e}")
        logger.error(traceback.format_exc())
        return exam


def scrape_solution(solution_url, document_schema, save_path, solution: Solution):
    # Create thread-specific logger
    logger = get_logger(f"scrape_solution_{threading.current_thread().name}")
    
    try:
        logger.info(f"Starting solution scrape: {solution_url}")
        
        drv = SeleniumDriver(headless=True)
        drv.get(solution_url)

        builder = TreeBuilder(drv.driver, document_schema)
        builder.full_build_layout_tree()
        builder.annotate_regular_tree()

        scraper = Scraper(drv.driver, builder.root_node, "Solution", save_path, solution)
        scraper.scraper_orchestrator()
        
        logger.info(f"Completed solution scrape")
        
        drv.close()
        return solution  # Return populated solution
        
    except Exception as e:
        logger.error(f"Error scraping solution: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return solution


def main():
    logger = get_logger("main")
    
    # Initialize database
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    db_repo = DatabaseRepository(supabase)
    db_prep = DatabasePreparation()

    # Load schemas...
    with open("schemas/gaokao_v1.json") as f:
        main_schema = json.load(f)
    with open("schemas/exam_pagev1.json") as f:
        document_schema = json.load(f)
    with open("schemas/template_config.json") as f:
        config = json.load(f)

    # Build main page tree...
    main_driver = SeleniumDriver(headless=True)
    main_driver.get("https://gaokao.eol.cn/e_html/gk/gkst/")
    
    main_builder = TreeBuilder(main_driver.driver, main_schema, config)
    main_builder.full_build_layout_tree()
    #exam_variant_node = main_builder.root_node.find_in_node("id", "st1")
    exam_variant_nodes = main_builder.root_node.find_in_node("class", "test",  find_all=True )
    for exam_variant_node in exam_variant_nodes:
        #i get all the sti nodes; store them then annotate each branch
        main_builder.annotate_sti_branch(exam_variant_node)
        subjects = exam_variant_node.find_in_node("tag", "li", find_all=True)
        
        save_path = r"C:\Users\user\Desktop\CEE\SeleniumBot\documents"
        # Process each subject
        for subj in subjects:
            try:
                links = subj.find_in_node("tag", "a", find_all=True)
                logger.info(f"Found {len(links)} links")
                
                # Validate links exist
                if not links or len(links) == 0:
                    logger.warning("No links found in subject, skipping")
                    continue
                
                # Get and validate exam URL
                exam_url = links[0].web_element.get_attribute("href")
                exam_text = links[0].web_element.text or "Unknown"
                
                # CRITICAL: Skip if exam URL is empty or None
                if not exam_url or exam_url.strip() == "":
                    logger.warning(f"Exam link is empty for '{exam_text}', skipping subject")
                    continue
                
                # Validate URL format
                if not exam_url.startswith("http"):
                    logger.warning(f"Invalid exam URL format: {exam_url}, skipping subject")
                    continue
                
                logger.info(f"Exam link: {exam_text} -> {exam_url}")
                
                # Get solution URL (optional)
                solution_url = None
                if len(links) > 1:
                    solution_url = links[1].web_element.get_attribute("href")
                    solution_text = links[1].web_element.text or "Unknown"
                    
                    # Validate solution URL if it exists
                    if solution_url and (solution_url.strip() == "" or not solution_url.startswith("http")):
                        logger.warning(f"Invalid solution URL: {solution_url}, will skip solution")
                        solution_url = None
                    
                    if solution_url:
                        logger.info(f"Solution link: {solution_text} -> {solution_url}")
                
                logger.info(f"Processing exam: {exam_url}")
                
                # Create dataclass instances
                exam_folder = os.path.join(save_path, "exam_temp")
                os.makedirs(exam_folder, exist_ok=True)
                exam = Exam(country="china", local_path=exam_folder, exam_url=exam_url)
                
                solution = None
                solution_folder = None
                if solution_url:
                    exam.solution_exist = True
                    solution_folder = os.path.join(save_path, "solution_temp")
                    os.makedirs(solution_folder, exist_ok=True)
                    solution = Solution(local_path=solution_folder, solution_url=solution_url)
                
                # Launch threads with results capture
                threads = []
                results = {}
                
                def exam_wrapper():
                    results['exam'] = scrape_exam(exam_url, document_schema, exam_folder, exam)
                
                def solution_wrapper():
                    results['solution'] = scrape_solution(solution_url, document_schema, solution_folder, solution)
                
                t1 = threading.Thread(target=exam_wrapper, name=f"exam_{exam.subject or 'unknown'}")
                t1.start()
                threads.append(t1)
                
                if solution_url:
                    t2 = threading.Thread(target=solution_wrapper, name=f"solution_{exam.subject or 'unknown'}")
                    t2.start()
                    threads.append(t2)
                
                # Wait for threads to complete
                for t in threads:
                    t.join()
                
                logger.info("Threads completed, preparing database insertion")
                
                # Prepare data for database
                exam_dict, solution_dict, document_links = db_prep.prepare_for_database(
                    results.get('exam', exam),
                    results.get('solution', solution)
                )
                
                # Insert into database
                try:
                    exam_id, solution_id = db_repo.insert_exam_with_relations(
                        exam_dict, solution_dict, document_links
                    )
                    logger.info(f"Successfully inserted exam_id={exam_id}, solution_id={solution_id}")
                except Exception as e:
                    logger.error(f"Failed to insert into database: {e}")
                    logger.error(traceback.format_exc())
            
            except Exception as e:
                logger.error(f"Error processing subject: {e}")
                logger.error(traceback.format_exc())
                continue  # Skip to next subject
    
    main_driver.close()
    logger.info("Main process completed")


if __name__ == "__main__":
    main()