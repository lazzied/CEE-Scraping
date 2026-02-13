"""
Instance assembly - coordinating metadata and document extraction from DOM.
"""

from dom_processing.my_scraper.document_retriever_implementations import (
    ChineseDirectLinkDocumentRetriever, 
    ChineseReferenceBasedDocumentRetriever
)
from .models import Instance
from .interfaces import TextParser, DocumentRetriever


class InstanceNodeManager:
    """Manages finding and classifying DOM nodes."""
    
    def find_target_nodes(self, root_node) -> list:
        """Find all nodes with metadata using DFS."""
        if not root_node:
            raise ValueError("root_node cannot be None")
        
        try:
            stack = [root_node]
            target_nodes = []
            
            while stack:
                current_node = stack.pop()
                
                if not hasattr(current_node, 'target_types'):
                    raise AttributeError(
                        f"Node missing 'target_types' attribute. Node type: {type(current_node).__name__}"
                    )
                
                if current_node.target_types:
                    target_nodes.append(current_node)
                
                if not hasattr(current_node, 'children'):
                    raise AttributeError(
                        f"Node missing 'children' attribute. Node type: {type(current_node).__name__}"
                    )
                
                for child in current_node.children:
                    stack.append(child)
                    
            return target_nodes
        except AttributeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to traverse DOM tree: {type(e).__name__}: {e}")

    def classify_target_nodes(self, target_nodes: list) -> tuple[list, list]:
        """Classify nodes into metadata and document nodes.
        
        Returns:
            Tuple of (metadata_nodes, document_nodes)
        """
        if not isinstance(target_nodes, list):
            raise TypeError(f"target_nodes must be a list, got {type(target_nodes).__name__}")

        instance_documents_target_nodes = []
        instance_metadata_target_nodes = []

        for i, target_node in enumerate(target_nodes):
            try:
                if not hasattr(target_node, 'target_types'):
                    print(f"Warning: Node {i} missing 'target_types' attribute, skipping")
                    continue
                
                if not target_node.target_types:
                    continue
                
                for target_type in target_node.target_types:
                    if not isinstance(target_type, str):
                        print(f"Warning: target_type is not a string (got {type(target_type).__name__}), skipping")
                        continue
                    
                    if target_type.endswith("_url"):
                        instance_documents_target_nodes.append(target_node)
                    else:
                        instance_metadata_target_nodes.append(target_node)
            except Exception as e:
                print(f"Warning: Error classifying node {i}: {type(e).__name__}: {e}")
                continue

        return instance_metadata_target_nodes, instance_documents_target_nodes



    



class InstanceAssembler:
    """Assembles complete instance from DOM tree."""
    
    def __init__(
        self, 
        text_parser: TextParser, 
        document_retriever: DocumentRetriever, 
        schema_queries,
    ):
        """Initialize with parsing and retrieval services."""
        if not text_parser:
            raise ValueError("text_parser cannot be None")
        if not document_retriever:
            raise ValueError("document_retriever cannot be None")
        if not schema_queries:
            raise ValueError("schema_queries cannot be None")
        
        self.text_parser = text_parser
        self.document_retriever = document_retriever
        self.schema_queries = schema_queries
        
        try:
            self.node_manager = InstanceNodeManager()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize InstanceAssembler components: {type(e).__name__}: {e}")
        
    def _set_instance_metadata_attributes(
    self,
    instance: Instance, 
    nodes: list, 
    text_parser: TextParser,
    root_node,
    driver
) -> None:
        """Set metadata attributes on instance from nodes."""
        if not instance:
            raise ValueError("instance cannot be None")
        if not hasattr(instance, 'metadata'):
            raise AttributeError(f"Instance missing 'metadata' attribute. Instance type: {type(instance).__name__}")
        if not isinstance(nodes, list):
            raise TypeError(f"nodes must be a list, got {type(nodes).__name__}")
        if not text_parser:
            raise ValueError("text_parser cannot be None")
        if not root_node:
            raise ValueError("root_node cannot be None")
        if not driver:
            raise ValueError("driver cannot be None")
        
        for i, target_node in enumerate(nodes):
            try:
                if not hasattr(target_node, 'target_types'):
                    print(f"Warning: Metadata node {i} missing 'target_types' attribute, skipping")
                    continue
                
                if not target_node.target_types:
                    continue
                
                for target_type in target_node.target_types:
                    if not isinstance(target_type, str):
                        print(f"Warning: target_type is not a string (got {type(target_type).__name__}), skipping")
                        continue
                    
                    if target_type.endswith("_url"):
                        continue  # Skip URL types in metadata processing
                    
                    try:
                        metadata_type, metadata_val = text_parser.get_metadata_value(
                            target_node, target_type, driver
                        )
                    except Exception as e:
                        print(f"Warning: Failed to parse metadata for target_type '{target_type}' "
                                f"from node {i}: {type(e).__name__}: {e}")
                        continue
                    
                    if not metadata_type:
                        print(f"Warning: Empty metadata_type returned for target_type '{target_type}' from node {i}")
                        continue
                    
                    if not hasattr(instance.metadata, metadata_type):
                        print(f"Warning: Instance metadata has no attribute '{metadata_type}', skipping")
                        continue
                    
                    try:
                        setattr(instance.metadata, metadata_type, metadata_val)
                    except Exception as e:
                        print(f"Warning: Failed to set instance.metadata.{metadata_type} = {metadata_val}: "
                                f"{type(e).__name__}: {e}")
                        continue
            except Exception as e:
                print(f"Warning: Error processing metadata node {i}: {type(e).__name__}: {e}")
                continue

    def _get_classified_nodes(self, root_node):
        """Helper to find and classify nodes."""
        if not root_node:
            raise ValueError("root_node cannot be None")
        
        try:
            all_nodes = self.node_manager.find_target_nodes(root_node)
        except Exception as e:
            raise RuntimeError(f"Failed to find target nodes: {e}")
        
        try:
            return self.node_manager.classify_target_nodes(all_nodes)
        except Exception as e:
            raise RuntimeError(f"Failed to classify target nodes: {e}")

    def set_instance_metadata_attributes(self, root_node, instance: Instance, driver):
        """Extract and set metadata attributes on instance."""
        if not root_node:
            raise ValueError("root_node cannot be None")
        if not instance:
            raise ValueError("instance cannot be None")
        if not driver:
            raise ValueError("driver cannot be None")
        
        try:
            meta_nodes, _ = self._get_classified_nodes(root_node)
        except Exception as e:
            raise RuntimeError(f"Failed to get classified nodes for metadata assembly: {e}")
        
        if not meta_nodes:
            print("Warning: No metadata nodes found in DOM tree")
            return
        
        try:
            self._set_instance_metadata_attributes(
                instance, meta_nodes, self.text_parser, root_node, driver
            )
        except Exception as e:
            raise RuntimeError(f"Failed to set instance metadata attributes: {e}")

    def set_instance_document_attributes(self, root_node, instance: Instance, state, driver):
        """Extract and set document attributes on instance using appropriate retrieval technique."""
        # Validate inputs
        if not root_node:
            raise ValueError("root_node cannot be None")
        if not instance:
            raise ValueError("instance cannot be None")
        if state not in ["exam", "solution"]:
            raise ValueError(f"Invalid state '{state}': must be 'exam' or 'solution'")
        if not driver:
            raise ValueError("driver cannot be None")
        
        # Get document nodes
        try:
            _, doc_nodes = self._get_classified_nodes(root_node)
        except Exception as e:
            raise RuntimeError(f"Failed to get classified nodes for document assembly (state={state}): {e}")
        
        if not doc_nodes:
            print(f"Warning: No document nodes found in DOM tree (state={state})")
            return
        
        # Determine document type attribute name
        document_type = "exam_path" if state == "exam" else "solution_path"
        
        # Use appropriate retrieval technique based on document retriever type
        if isinstance(self.document_retriever, ChineseReferenceBasedDocumentRetriever):
            self._set_reference_based_document(doc_nodes, root_node, instance, state, driver, document_type)
        elif isinstance(self.document_retriever, ChineseDirectLinkDocumentRetriever):
            self._set_direct_link_document(doc_nodes, root_node, instance, state, driver, document_type)
        else:
            raise TypeError(f"Unknown document retriever type: {type(self.document_retriever).__name__}")

    def _set_reference_based_document(self, doc_nodes, root_node, instance, state, driver, document_type):
        """Handle reference-based document retrieval (uses first node only)."""
        target_node = doc_nodes[0]
        
        try:
            document_path = self.document_retriever.construct_document(
                target_node, root_node, instance, state, driver
            )
        except Exception as e:
            raise RuntimeError(f"Document construction failed for {state}: {e}")
        
        if not document_path:
            raise RuntimeError(f"Empty document_path returned for {state}")
        
        if not hasattr(instance.documents, document_type):
            raise AttributeError(f"Instance documents has no attribute '{document_type}'")
        
        try:
            setattr(instance.documents, document_type, document_path)
        except Exception as e:
            raise RuntimeError(f"Failed to set instance.documents.{document_type}: {e}")

    def _set_direct_link_document(self, doc_nodes, root_node, instance, state, driver, document_type):
        """Handle direct-link document retrieval (processes all nodes)."""
        try:
            document_path = self.document_retriever.construct_document(
                doc_nodes, root_node, instance, state, driver
            )
        except Exception as e:
            raise RuntimeError(f"Document construction failed for {state}: {e}")
        
        if not document_path:
            raise RuntimeError(f"Empty document_path returned for {state}")
        
        if not hasattr(instance.documents, document_type):
            raise AttributeError(f"Instance documents has no attribute '{document_type}'")
        
        try:
            setattr(instance.documents, document_type, document_path)
        except Exception as e:
            raise RuntimeError(f"Failed to set instance.documents.{document_type}: {e}")