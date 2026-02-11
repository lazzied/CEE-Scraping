import os
from supabase import create_client
from db.database_prepare import DatabasePreparation
from db.database_repo import DatabaseRepository
from dom.selenium_driver import SeleniumDriver
from dom_processing.config.scraper_config import ScraperConfig
from dom_processing.dom_tree_builder.tree_building.tree_building_entry_point import BuildTree
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.dom_tree_builder.tree_annotation.annotate_tree import AnnotateTree
from dom_processing.instance_tracker import Tracker
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from dom_processing.my_scraper.chinese_retriever import ChineseDocumentRetriever, ChineseTextParser
from dom_processing.my_scraper.instance_assembler import InstanceAssembler
from dom_processing.my_scraper.models import Instance



def initialize_supabase():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    return supabase

def get_scraper_config_info(path):
    scraper_config_inst = ScraperConfig(path)
    scraper_config_inst.load_config()
    page_url = scraper_config_inst.get_page_url()
    schema_paths = scraper_config_inst.get_schema_paths()

    return page_url , schema_paths

def ChineseMain() -> Instance:
    supabase = initialize_supabase()

    tracker = Tracker(supabase) # will check it later
    tracker.set_database_instances()

    # this gets a path and return 
    main_page_url, main_schema_paths = get_scraper_config_info("dom_processing/config/main_scraper_config.json")
    document_page_url, document_schema_paths = get_scraper_config_info("dom_processing/config/document_scraper_config.json")
    

    selenium_driver = SeleniumDriver(True)
    tree_builder = BuildTree()
    main_page_node_tree =tree_builder.build(main_page_url,main_schema_paths)
    document_page_node_tree=tree_builder.build(document_page_url,document_schema_paths)
    
    st_branch_nodes = main_page_node_tree.find_in_node("id","st{1-33!2,4}",True)
    for st_branch_node in st_branch_nodes:

        st_branch_annotator = AnnotateTree()
        st_branch_schema_query = SchemaQueries(main_schema_paths["page_schema"]["main_schema"])
        template_registry = TemplateRegistry(main_schema_paths["templates_schema"])
        config_queries = ConfigQueries(main_schema_paths["config_schema"])
        selenium_finder = SeleniumElementFinder()
        cache_handler = HandleCaching(selenium_finder)
        selector_builder = SelectorBuilder(template_registry,config_queries)

        st_branch_caching_coordinator = CachingCoordinator(cache_handler,selector_builder,st_branch_schema_query)

        
        st_branch_annotator.annotate_tree(st_branch_node,st_branch_caching_coordinator,st_branch_schema_query)
        subject_nodes = st_branch_node.find_in_node("tag","li",True)
        for subject_node in subject_nodes:
            url_nodes = subject_node.find_in_node("tag","a",True)
             # this need to be adjusted in the annotation; specific for the chinese case
            #we suppose that the nodes are correctly annotated
            if url_nodes: #exam link exists 
                exam_node = url_nodes[0]
                exam_url = exam_node.web_element.get_attribute("href")
                #here i should see if i already added it to the database and it exists in the local storage and later check on cloud storage

                selenium_driver.get(exam_url)
                 #went to the next page: exam

                instance = Instance()

                document_annotator = AnnotateTree()
                document_schema_query = SchemaQueries(document_schema_paths["page_schema"]["main_schema"])
                document_template_registry = TemplateRegistry(document_schema_paths["templates_schema"])
                document_config_queries = ConfigQueries(document_schema_paths["config_schema"])
                selenium_finder = SeleniumElementFinder()
                cache_handler = HandleCaching(selenium_finder)
                selector_builder = SelectorBuilder(document_template_registry,document_config_queries)
                document_caching_coordinator = CachingCoordinator(cache_handler,selector_builder,document_schema_query)

                document_annotator.annotate_tree(document_page_node_tree,document_caching_coordinator,document_schema_query)
                
                chinese_exam_document_retriever = ChineseDocumentRetriever(selenium_driver)
                chinese_text_parser = ChineseTextParser()

                instance_assembler = InstanceAssembler(chinese_text_parser,chinese_exam_document_retriever, document_schema_query)
                instance_assembler.assemble_instance_metadata_attributes(document_page_node_tree,instance)
                instance_assembler.assemble_instance_documents_attributes(document_page_node_tree,instance)
            
                if len(url_nodes) == 2:
                     #solution also exists
                    solution_node =url_nodes[1]
                    solution_url = solution_node.web_element.get_attribute("href")
                    #here i should see if i already added it to the database and it exists in the local storage and later check on cloud storage

                    selenium_driver.get(solution_url)


                    document_annotator.annotate_tree(document_page_node_tree,document_caching_coordinator,document_schema_query)
                    chinese_solution_document_retriever = ChineseDocumentRetriever(selenium_driver)
                    instance_assembler = InstanceAssembler(chinese_text_parser,chinese_solution_document_retriever, document_schema_query)
                    instance_assembler.assemble_instance_documents_attributes(document_page_node_tree,instance)

    

    db_repo = DatabaseRepository(supabase)
    db_prep = DatabasePreparation()

    
    
                
            


