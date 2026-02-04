import json
from pathlib import Path

class ScraperConfig:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @property
    def main_page_url(self) -> str:
        return self._config['page']['url']
    
    @property
    def schema_paths(self) -> dict:
        return self._config['schema_paths']
    
    def get_target_config(self, target_name: str) -> dict:
        """Get configuration for a specific scraping target"""
        return self._config['targets'].get(target_name)