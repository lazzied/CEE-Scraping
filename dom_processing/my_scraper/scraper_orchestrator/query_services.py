from pathlib import Path

from dom_processing.config.scraper_config import ScraperConfig
from dom_processing.json_parser import ConfigQueries, SchemaQueries, TemplateRegistry
from utils import load_json_from_project


class QueryServices:
    """Loads and manages scraper configuration and schemas."""
    
    PROJECT_ROOT = Path("C:/Users/user/Desktop/CEE/SeleniumBot/json_schemas")
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.page_url = None
        self.schema_queries = None
        self.config_queries = None
        self.template_registry = None
    
    def initialize_query_services(self) -> 'QueryServices':
        """Load all configuration and schema files."""
        try:
            scraper_config = ScraperConfig(self.config_path)
            scraper_config.load_config()
            
            self.page_url = scraper_config.get_page_url()
            if not self.page_url:
                raise ValueError(f"Page URL not found in config file: {self.config_path}")
            
            schema_paths = scraper_config.get_schema_paths()
            if not schema_paths:
                raise ValueError(f"Schema paths not found in config file: {self.config_path}")
            
            # Load schemas
            if "page_schema" not in schema_paths:
                raise KeyError(f"'page_schema' key missing in schema_paths from config: {self.config_path}")
            
            try:
                page_schema = load_json_from_project(
                    schema_paths["page_schema"],
                    str(self.PROJECT_ROOT)
                )
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Page schema file not found: {schema_paths['page_schema']} "
                    f"(Project root: {self.PROJECT_ROOT})"
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load page schema from {schema_paths['page_schema']}: {e}")

            try:
                self.schema_queries = SchemaQueries(page_schema)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize SchemaQueries with page schema: {e}")

            if "templates_config" in schema_paths:
                try:
                    config_schema = load_json_from_project(
                        schema_paths["templates_config"],
                        str(self.PROJECT_ROOT)
                    )
                    self.config_queries = ConfigQueries(config_schema)
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Templates config file not found: {schema_paths['templates_config']} "
                        f"(Project root: {self.PROJECT_ROOT})"
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load templates config from {schema_paths['templates_config']}: {e}")

            if "templates" in schema_paths:
                try:
                    templates_schema = load_json_from_project(
                        schema_paths["templates"],
                        str(self.PROJECT_ROOT)
                    )
                    self.template_registry = TemplateRegistry(templates_schema)
                except FileNotFoundError:
                    raise FileNotFoundError(
                        f"Templates file not found: {schema_paths['templates']} "
                        f"(Project root: {self.PROJECT_ROOT})"
                    )
                except Exception as e:
                    raise RuntimeError(f"Failed to load templates from {schema_paths['templates']}: {e}")
                
            return self
        except (FileNotFoundError, ValueError, KeyError, RuntimeError):
            raise
        except Exception as e:
            raise RuntimeError(f"Unexpected error initializing query services from {self.config_path}: {type(e).__name__}: {e}")
