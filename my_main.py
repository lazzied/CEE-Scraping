import os

from dotenv import load_dotenv
from dom_processing.instance_tracker import Tracker
from dom_processing.my_scraper.scraper_orchestrator.scraper_orchestrator import ScraperOrchestrator
from db.database_repo import DatabaseRepository
from supabase import create_client


def main():
    load_dotenv()

    # Get Supabase credentials from environment
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    # Validate credentials exist
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    db_repository = DatabaseRepository(supabase)
    instance_tracker = Tracker(supabase)
    try:
        orchestrator = ScraperOrchestrator(
            main_scraper_config_path="dom_processing/config/main_scraper_config.json",
            document_scraper_config_path="dom_processing/config/document_scraper_config.json",
            fallback_document_scraper_config_path="dom_processing/config/fallback_document_scraper_config.json",  # <-- ADD COMMA HERE
            database_repository=db_repository,
            instance_tracker = instance_tracker
        )
        orchestrator.run()
    except Exception as e:
        print(f"Fatal error in main: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()