from typing import List, TypedDict

class ChatResponse(TypedDict):
    relevant_source_ids: List[int]
    answer: str

class BaseAPI():

    def num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        num_tokens = 0
        return num_tokens


    def retrieve_response(self, question: str, relevant_docs: list[dict]) -> ChatResponse:        
        """
        Given a question and a list of relevant docs, returns a response with at least an text answer
        """
        response: ChatResponse = response
        return response