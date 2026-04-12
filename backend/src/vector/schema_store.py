"""
OmniData — Schema Store

Thin wrapper over PineconeClient for the schema_store namespace.
Retrieves relevant Snowflake table schemas for a given query.
"""

import logging
from src.vector.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)


class SchemaStore:
    """Retrieves relevant table schemas from Pinecone schema_store namespace."""
    
    NAMESPACE = "schema_store"
    
    def __init__(self, pinecone_client: PineconeClient, index_name: str):
        self.client = pinecone_client
        self.index_name = index_name
    
    def get_relevant_schemas(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Find the most relevant table schemas for a user query.
        
        Returns list of matches with schema text and metadata.
        """
        matches = self.client.hybrid_query(
            index_name=self.index_name,
            namespace=self.NAMESPACE,
            query_text=query,
            top_k=top_k,
        )
        
        schemas = []
        for match in matches:
            schemas.append({
                "table_name": match["metadata"].get("table_name", "unknown"),
                "schema": match["metadata"].get("schema", "unknown"),
                "description": match["metadata"].get("text", ""),
                "relevance_score": match["score"],
            })
        
        logger.info(f"Schema RAG: {len(schemas)} tables matched for query")
        return schemas


class ExamplesStore:
    """Retrieves relevant Q→SQL examples from Pinecone examples_store namespace."""
    
    NAMESPACE = "examples_store"
    
    def __init__(self, pinecone_client: PineconeClient, index_name: str):
        self.client = pinecone_client
        self.index_name = index_name
    
    def get_relevant_examples(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Find the most relevant Q→SQL examples for few-shot prompting.
        
        Returns list of matches with example text and metadata.
        """
        matches = self.client.hybrid_query(
            index_name=self.index_name,
            namespace=self.NAMESPACE,
            query_text=query,
            top_k=top_k,
        )
        
        examples = []
        for match in matches:
            examples.append({
                "example_text": match["metadata"].get("text", ""),
                "category": match["metadata"].get("category", ""),
                "relevance_score": match["score"],
            })
        
        logger.info(f"Examples RAG: {len(examples)} examples matched for query")
        return examples
