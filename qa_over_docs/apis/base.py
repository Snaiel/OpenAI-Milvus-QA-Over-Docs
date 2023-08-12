from typing import List, TypedDict

class ChatResponse(TypedDict):
    relevant_source_ids: List[int]
    answer: str

class BaseAPI():
    def __init__(self, system_instructions, user_reminder, max_token_length) -> None:
        self.system_instructions = system_instructions
        self.user_reminder = user_reminder
        self.max_token_length = max_token_length


    def num_tokens_from_string(self, string: str) -> int:
        """Returns the number of tokens in a text string."""
        num_tokens = 0
        return num_tokens


    def get_messages_token_length(self, messages: list[dict]):
        """Returns the total amount of tokens in the messages list"""
        content = [i["content"] for i in messages]
        return self.num_tokens_from_string("\n".join(content))


    def retrieve_response(self, question: str, relevant_docs: list[dict]) -> ChatResponse:        
        """
        Given a question and a list of relevant docs, returns a response with at least an text answer
        """
        response: ChatResponse = response
        return response