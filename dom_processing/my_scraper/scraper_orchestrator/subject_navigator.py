class SubjectNavigator:
    """Navigates through subjects and extracts exam URLs."""
    
    @staticmethod
    def get_documents_url(subject_node) -> dict:
        """Extract exam and solution URLs from subject node.
        
        Returns:
            Dictionary with 'exam_page_url' and/or 'solution_page_url' keys
        """
        if not subject_node:
            raise ValueError("subject_node cannot be None")
        
        try:
            a_nodes = subject_node.find_in_node("tag", "a", True)
        except Exception as e:
            raise RuntimeError(f"Failed to find <a> tags in subject node: {type(e).__name__}: {e}")
        
        if not a_nodes:
            return {}
        
        document_urls = {}
        
        for node in a_nodes:
            try:
                if not hasattr(node, 'target_types'):
                    continue
                
                if "exam" in node.target_types:
                    if not hasattr(node, 'web_element'):
                        print(f"Warning: Node with 'exam' target_type has no web_element attribute")
                        continue
                    try:
                        href = node.web_element.get_attribute("href")
                        if href:
                            document_urls["exam_page_url"] = href
                    except Exception as e:
                        print(f"Warning: Failed to get href for exam node: {e}")
                
                if "solution" in node.target_types:
                    if not hasattr(node, 'web_element'):
                        print(f"Warning: Node with 'solution' target_type has no web_element attribute")
                        continue
                    try:
                        href = node.web_element.get_attribute("href")
                        if href:
                            document_urls["solution_page_url"] = href
                    except Exception as e:
                        print(f"Warning: Failed to get href for solution node: {e}")
            except Exception as e:
                print(f"Warning: Error processing node for URLs: {e}")
                continue
        
        return document_urls
