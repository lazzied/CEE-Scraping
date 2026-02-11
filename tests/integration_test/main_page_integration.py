
from dom_processing.config.scraper_config import ScraperConfig
from dom_processing.dom_tree_builder.tree_building.tree_building_entry_point import BuildTree
from dom_processing.dom_tree_builder.caching.cache import HandleCaching
from dom_processing.dom_tree_builder.caching.coordinators import CachingCoordinator
from dom_processing.dom_tree_builder.caching.finders import SeleniumElementFinder
from dom_processing.dom_tree_builder.caching.selectors import SelectorBuilder
from dom_processing.dom_tree_builder.tree_annotation.annotate_tree import AnnotateTree
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from utils import load_json_from_project




def get_scraper_config_info(path):
    scraper_config_inst = ScraperConfig(path)
    scraper_config_inst.load_config()
    page_url = scraper_config_inst.get_page_url()
    schema_paths = scraper_config_inst.get_schema_paths()

    return page_url , schema_paths


def main():
    # this gets a path and return 
    main_page_url, main_page_schema_paths = get_scraper_config_info("dom_processing/config/main_scraper_config.json")


    tree_builder = BuildTree()

    page_schema_bundle = load_json_from_project(main_page_schema_paths["page_schema"],"C:/Users/user/Desktop/CEE/SeleniumBot/json_schemas")
    config_schema = load_json_from_project(main_page_schema_paths["config"],"C:/Users/user/Desktop/CEE/SeleniumBot/json_schemas")
    templates_schema = load_json_from_project(main_page_schema_paths["templates"],"C:/Users/user/Desktop/CEE/SeleniumBot/json_schemas")

    main_page_schema_queries = SchemaQueries(page_schema_bundle)
    main_page_config_queries = ConfigQueries(config_schema)
    main_page_template_registry = TemplateRegistry(templates_schema)

    main_page_node_tree = tree_builder.build(main_page_url,
                                            main_page_schema_queries,
                                            main_page_config_queries,
                                            main_page_template_registry
                                            )
    main_page_node_tree.print_dom_tree()

    """
    st_branch_nodes = main_page_node_tree.find_in_node("id","st{1-33!2,4}",True)

    for st_branch_node in st_branch_nodes:

        st_branch_annotator = AnnotateTree()
        selenium_finder = SeleniumElementFinder()
        cache_handler = HandleCaching(selenium_finder)
        selector_builder = SelectorBuilder(main_page_template_registry,main_page_config_queries)
        st_branch_caching_coordinator = CachingCoordinator(cache_handler,selector_builder,main_page_schema_queries)

       
        st_branch_annotator.annotate_tree(st_branch_node,st_branch_caching_coordinator,main_page_schema_queries)
       """
    
if __name__ == "__main__":
    main()
