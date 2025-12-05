from test_functions import get_logger

from tree_builder import TreeBuilder
from selenium_driver import SeleniumDriver
from my_dataclasses import Exam
from exam_solution_scraper import Scraper

import json
from selenium.common.exceptions import NoSuchElementException



def scrape_exam(exam_url, document_schema, save_path, exam: Exam):
    # Create thread-specific logger
    logger = get_logger("test_dom_changes")
    
    logger.info(f"Starting exam scrape: {exam_url}")
    
    drv = SeleniumDriver(headless=True)
    drv.get(exam_url)
    builder = TreeBuilder(drv.driver, document_schema)
    
    try:
        builder.full_build_layout_tree()
    except NoSuchElementException as e:
        print(f"builder failed on main schema: {e}")
        raise
    try:
        builder.annotate_regular_tree()
    except NoSuchElementException as e:
        print(f"builder failed on main schema: {e}")
        raise
    
    scraper = Scraper(drv.driver, builder.root_node, "Exam", save_path, exam)
    scraper.scraper_orchestrator()
    
    logger.info(f"Completed exam scrape: {exam.subject}")
    
    drv.close()
    return exam

exam_url = "http://127.0.0.1:5500/exam_page_test.html"

with open("schemas/exam_pagev1.json") as f:
    document_schema = json.load(f)

save_path =r"C:\Users\user\Desktop\CEE\SeleniumBot\documents\exam_temp"

exam = Exam(country = "china")

with open("schemas/exam_pagev2.json") as f:
    backup_schema = json.load(f)

try:
    scrape_exam(exam_url,document_schema, save_path,exam)
except NoSuchElementException :
    print("error happened, rerunning the builder")
    scrape_exam(exam_url,backup_schema,save_path,exam)
