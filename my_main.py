import os
from supabase import create_client
from db.database_prepare import DatabasePreparation
from db.database_repo import DatabaseRepository
from dom.selenium_driver import SeleniumDriver
from dom_processing.config.scraper_config import ScraperConfig
from dom_processing.dom_tree_builder.build_and_annotate import BuildAndAnnotate, BuildTree
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.dom_tree_builder.tree_annotation.annotate_tree import AnnotateTree
from dom_processing.instance_tracker import Tracker
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from dom_processing.my_scraper.chinese_retriever import ChineseDocumentRetriever, ChineseTextParser
from dom_processing.my_scraper.instance_assembler import InstanceAssembler
from dom_processing.my_scraper.interfaces import TextParser
from dom_processing.my_scraper.models import Instance


def initialize_supabase():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    return supabase

def ChineseMain() -> Instance:
    supabase = initialize_supabase()

    tracker = Tracker(supabase) # will check it later

    tracker.set_database_instances()
    
    #here we need to decide, if the page will be reused multiple times or the page is going to be built and annotated then discarded
    # here you write the code for the country
    """
    here's the simplified algorithm: 


    build the main page tree
    build the exam page tree
    now enter the main page tree: gather all the st{index}
    then iterate over them, one by one:
        annotate branch #here will raise error if an a tag does not exist
        get the subject nodes <li> tags
        for subject node in subject nodes

            initialize an instance
            if exam link exists:
                go to exam page
                get the exam page tree; annotate it
                set the exam metadata + document.exampath
            else:
                coninue
            if solution link exist:
                go to solution link
                set document.solutionpath
            else:
                document.solutionpath = ""
"dom_processing/config/main_scraper_config.json"
    """
    main_scraper_config = ScraperConfig("dom_processing/config/main_scraper_config.json")
    main_scraper_config._load_config()
    main_page_url = main_scraper_config.main_page_url()
    main_schema_paths = main_scraper_config.schema_paths()

    document_scraper_config = ScraperConfig("dom_processing/config/document_scraper_config.json")
    document_scraper_config._load_config()
    document_page_url = document_scraper_config.main_page_url()
    document_schema_paths = document_scraper_config.schema_paths()




    selenium_driver = SeleniumDriver(True)
    tree_builder = BuildTree()
    main_page_node_tree =tree_builder.build(main_page_url,main_schema_paths)
    document_page_node_tree=tree_builder.build(document_page_url,document_schema_paths)
    
    #hard coded as shit
    st_branch_nodes = main_page_node_tree.find_in_node("id","st{1-33!2,4}",True)
    for st_branch_node in st_branch_nodes:

        st_branch_annotator = AnnotateTree()


        st_branch_schema_query = SchemaQueries(main_schema_paths["page_schema"])
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
                document_schema_query = SchemaQueries(document_schema_paths["page_schema"])
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

    
                    # i should only get the document, no metadata needed bu the assemble

    db_repo = DatabaseRepository(supabase)
    db_prep = DatabasePreparation()

    """
    todo:
    Marathon:
    in order:
        
        - fix json & global parameters
        - update schemaquery functions
        - add target types for the nodes and
        - polish code so the schema switching is easy
        - build and annotate.py ??? reform it better
        - fix namings
        - finish main
        - reform everything: what is specific to china and what is shared across all instances
        - run independed integration tests
        - test and polish until it succedes

        - integrate database
        - integrate tracker
        - test and polish until it succedes

        - check scalibility possibilities and edit code accordingly=
        - run tests on 2025/2024 gaokao
        - test and polish until it succedes

        - final improvements
        - write rules and documentation 
        - use that and create rigorous validation methods
        - setup github
    """

    
                
            


