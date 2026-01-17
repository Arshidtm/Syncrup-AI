import openai
import os
from typing import List

class VectorSync:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key

    def generate_embedding(self, text: str):
        """Generates embedding for a code block."""
        try:
            response = openai.Embedding.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"Embedding error: {e}")
            return None

    def sync_to_milvus(self, node_id: str, embedding: List[float], metadata: dict):
        """
        Placeholder for Milvus/Pinecone synchronization.
        In a full implementation, this uses the pymilvus library.
        """
        print(f"Syncing Vector for Node {node_id} to Milvus...")
        # milvus_client.insert(collection, [[embedding]], [metadata])
        pass

    def code_to_vector_context(self, code_blocks: List[dict]):
        """Processes a list of definitions and generates vectors."""
        for block in code_blocks:
            # We embed the function name and some context
            text_to_embed = f"{block['type']} {block['name']} in {block.get('filename', 'unknown')}"
            vector = self.generate_embedding(text_to_embed)
            if vector:
                self.sync_to_milvus(block['name'], vector, block)
