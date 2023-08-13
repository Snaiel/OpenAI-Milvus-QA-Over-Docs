from typing import List, TypedDict
from langchain.embeddings.base import Embeddings

class ChatResponse(TypedDict):
    relevant_source_ids: List[int]
    answer: str

class BaseAPI(Embeddings):

    def num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        return None


    def retrieve_response(self, question: str, relevant_docs: list[dict]) -> ChatResponse:        
        """
        Given a question and a list of relevant docs, returns a response with at least an text answer
        """
        response: ChatResponse = response
        return response
    

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
    

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""