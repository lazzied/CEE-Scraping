import json
from pathlib import Path

class ScraperConfig:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_page_url(self) -> str:
        return self.config['page']['url']
    
    def get_schema_paths(self) -> dict:
        return self.config['schema_paths']
    
    def get_target_config(self, target_name: str) -> dict:
        """Get configuration for a specific scraping target"""
        return self.config['targets'].get(target_name)