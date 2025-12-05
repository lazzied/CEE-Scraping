import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class CheckpointManager:
    """Manages scraping progress to enable resume on crash."""
    
    def __init__(self, checkpoint_file: str = "scraping_checkpoint.json"):
        self.checkpoint_file = checkpoint_file
        self.checkpoint_data = self._load_checkpoint()
    
    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load existing checkpoint or create new one."""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading checkpoint: {e}, starting fresh")
        
        return {
            "last_variant_index": 0,
            "last_subject_index": 0,
            "completed_exams": [],
            "last_updated": None,
            "session_start": datetime.now().isoformat(),
            "schema_failures": dict()
        }
    
    def save_checkpoint(self, variant_idx: int, subject_idx: int, exam_url: str):
        """Save current progress."""
        self.checkpoint_data.update({
            "last_variant_index": variant_idx,
            "last_subject_index": subject_idx,
            "last_updated": datetime.now().isoformat()
        })
        
        # Track completed exams to avoid duplicates
        if exam_url not in self.checkpoint_data["completed_exams"]:
            self.checkpoint_data["completed_exams"].append(exam_url)
        
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.checkpoint_data, f, indent=2)
    
    def should_skip(self, variant_idx: int, subject_idx: int, exam_url: str) -> bool:
        """Determine if this item should be skipped (already processed)."""
        # Skip if we're before the checkpoint
        if variant_idx < self.checkpoint_data["last_variant_index"]:
            return True
        
        if variant_idx == self.checkpoint_data["last_variant_index"]:
            if subject_idx <= self.checkpoint_data["last_subject_index"]:
                return True
        
        # Also check if exam was already completed
        if exam_url in self.checkpoint_data["completed_exams"]:
            return True
        
        return False
    
    def reset(self):
        """Clear checkpoint to start from beginning."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
        self.checkpoint_data = self._load_checkpoint()
    
    def get_resume_info(self) -> str:
        """Get readable resume information."""
        if self.checkpoint_data["last_updated"]:
            return (f"Resuming from variant {self.checkpoint_data['last_variant_index']}, "
                   f"subject {self.checkpoint_data['last_subject_index']}. "
                   f"Already completed: {len(self.checkpoint_data['completed_exams'])} exams")
        return "Starting fresh scrape"
    
    def record_schema_failure(self, url: str, schema_name: str):
        """Record that a URL failed with a specific schema."""
        self.checkpoint_data["schema_failures"][url] = schema_name
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.checkpoint_data, f, indent=2)

    def get_failed_schema(self, url: str) -> Optional[str]:
        """Get which schema failed for this URL (if any)."""
        return self.checkpoint_data.get("schema_failures", {}).get(url)