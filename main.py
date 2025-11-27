from selenium_driver import SeleniumDriver
import os, sys, json, threading
from tree_builder import TreeBuilder
from exam_solution_scraper import Scraper


def scrape_exam(exam_url, document_schema, save_path):
    drv = SeleniumDriver(headless=True)
    drv.get(exam_url)

    builder = TreeBuilder(drv.driver, document_schema)
    builder.full_build_layout_tree()
    builder.annotate_regular_tree()

    scraper = Scraper(drv.driver,builder.root_node,"Exam",save_path)
    scraper.scraper_orchestrator()

    builder.root_node.print_dom_tree()

    drv.close()


def scrape_solution(solution_url,document_schema,save_path):
    drv = SeleniumDriver(headless=True)
    drv.get(solution_url)

    builder = TreeBuilder(drv.driver, document_schema)
    builder.full_build_layout_tree()
    builder.annotate_regular_tree()

    scraper = Scraper(drv.driver,builder.root_node,"Solution",save_path)
    scraper.scraper_orchestrator()

    builder.root_node.print_dom_tree()

    drv.close()


def main():
    #this will suppress all print statements in the code below
    sys.stdout = open(os.devnull, 'w')


    with open("schemas/gaokao_v1.json") as f:
        main_schema = json.load(f)

    with open("schemas/exam_pagev1.json") as f:
        document_schema = json.load(f)

    with open("schemas/template_config.json") as f:
        config = json.load(f)

    main_driver = SeleniumDriver(headless=True)
    main_driver.get("https://gaokao.eol.cn/e_html/gk/gkst/")

    main_builder = TreeBuilder(main_driver.driver, main_schema, config)
    main_builder.full_build_layout_tree()

    exam_variant_node = main_builder.root_node.find_in_node("id", "st1")
    main_builder.annotate_sti_branch(exam_variant_node)

    subjects = exam_variant_node.find_in_node("tag", "li", find_all=True)

    save_path = r"C:\Users\user\Desktop\CEE\SeleniumBot\documents"

    for subj in subjects:
        links = subj.find_in_node("tag", "a", find_all=True)
        
        exam_url = links[0].web_element.get_attribute("href")
        solution_url = links[1].web_element.get_attribute("href")
        
        threads = []
        
        if exam_url:
            exam_folder = os.path.join(save_path, "exam_temp")
            os.makedirs(exam_folder, exist_ok=True)
            t1 = threading.Thread(
                target=scrape_exam,
                args=(exam_url, document_schema, exam_folder)
            )
            t1.start()
            threads.append(t1)
        
        if solution_url:
            solution_folder = os.path.join(save_path, "solution_temp")
            os.makedirs(solution_folder, exist_ok=True)
            t2 = threading.Thread(
                target=scrape_solution,
                args=(solution_url, document_schema, solution_folder)
            )
            t2.start()
            threads.append(t2)
        
        for t in threads:
            t.join()

    main_driver.close()



if __name__ == "__main__":
    main()
