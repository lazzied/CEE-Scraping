from selenium import webdriver
import json
from tree_builder import TreeBuilder
from exam_solution_scraper import Scraper

driver = webdriver.Chrome()


test_link = r"https://gaokao.eol.cn/shiti/yy/202506/t20250612_2674288.shtml"
try:
    with open("schemas/exam_pagev1.json", "r") as f:
        scraper_schema = json.load(f)
    scraper_tree_builder = TreeBuilder(driver,test_link,scraper_schema)
    test_scraper = Scraper(scraper_tree_builder,"Exam",r"C:\Users\user\Desktop\CEE\SeleniumBot\documents")
    test_scraper.scraper_orchestrator()
except:
    print("didn't work cuh")