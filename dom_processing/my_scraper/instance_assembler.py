"""
Instance assembly - coordinating metadata and document extraction from DOM.
"""

from models import Instance, MetadataTypes
from interfaces import TextParser, DocumentRetriever


class InstanceNodeManager:
    """Manages finding and classifying DOM nodes."""
    
    def find_target_nodes(self, root_node) -> list:
        """Find all nodes with metadata using DFS."""
        stack = [root_node]
        target_nodes = []
        
        while stack:
            current_node = stack.pop()
            if current_node.metadata:
                target_nodes.append(current_node)
            for child in current_node.children:
                stack.append(child)
                
        return target_nodes

    def classify_target_nodes(self, target_nodes: list) -> tuple[list, list]:
        """Classify nodes into metadata and document nodes.
        
        Returns:
            Tuple of (metadata_nodes, document_nodes)
        """
        instance_documents_target_nodes = []
        
        for target_node in target_nodes:
            if (MetadataTypes.EXAM in target_node.metadata_types or 
                MetadataTypes.SOLUTION in target_node.metadata_types):
                instance_documents_target_nodes.append(target_node)

        instance_metadata_target_nodes = [
            node for node in target_nodes 
            if node not in instance_documents_target_nodes
        ]
        
        return instance_metadata_target_nodes, instance_documents_target_nodes


class InstanceDataSetter:
    """Sets instance attributes from parsed node data."""
    
    def set_instance_metadata_attributes(
        self, 
        instance: Instance, 
        nodes: list, 
        text_parser: TextParser
    ) -> None:
        """Extract and set metadata attributes from nodes."""
        for target_node in nodes:
            text_content = target_node.web_element.text
            filtered_metadata_type = [
                t for t in target_node.metadata_types
                if t not in [MetadataTypes.EXAM, MetadataTypes.SOLUTION]
            ]

            if len(filtered_metadata_type) == 1:
                metadata_type = filtered_metadata_type[0]
                parsed_val = text_parser.get_single_metadata_value(
                    text_content, metadata_type.value
                )
                setattr(instance.metadata, metadata_type.value, parsed_val)
            else:
                parsed_dict = text_parser.get_multiple_metadata_values(
                    text_content, [t.value for t in filtered_metadata_type]
                )
                for key, value in parsed_dict.items():
                    setattr(instance.metadata, key, value)

    def set_instance_documents_attributes(
        self,
        instance: Instance,
        nodes: list,
        document_retriever: DocumentRetriever,
        schema_queries
    ) -> None:
        """Extract and set document paths from nodes."""
        for target_node in nodes:
            if MetadataTypes.EXAM in target_node.metadata_types:
                exam_path = document_retriever.construct_document(
                    target_node, instance, schema_queries
                )
                instance.documents.exam_path = exam_path
            elif MetadataTypes.SOLUTION in target_node.metadata_types:
                sol_path = document_retriever.construct_document(
                    target_node, instance, schema_queries
                )
                instance.documents.solution_path = sol_path


class InstanceAssembler:
    """Assembles complete instance from DOM tree."""
    
    def __init__(
        self, 
        text_parser: TextParser, 
        document_retriever: DocumentRetriever, 
        schema_queries,
    ):
        """Initialize with parsing and retrieval services.
        
        Args:
            text_parser: Service for parsing text to metadata
            document_retriever: Service for retrieving documents
            schema_queries: Service for schema queries
        """
        self.text_parser = text_parser
        self.document_retriever = document_retriever
        self.schema_queries = schema_queries
        self.node_manager = InstanceNodeManager()
        self.data_setter = InstanceDataSetter()

    def assemble_instance_metadata_attributes(self, root_node, instance: Instance):
          all_nodes = self.node_manager.find_target_nodes(root_node)
          meta_nodes = self.node_manager.classify_target_nodes(all_nodes)[0]

          self.data_setter.set_instance_metadata_attributes(
                instance, meta_nodes, self.text_parser
            )   
    def assemble_instance_documents_attributes(self, root_node, instance: Instance):
        all_nodes = self.node_manager.find_target_nodes(root_node)
        doc_nodes = self.node_manager.classify_target_nodes(all_nodes)[1]

        self.data_setter.set_instance_documents_attributes(
            instance, doc_nodes, self.document_retriever, self.schema_queries
        ) 