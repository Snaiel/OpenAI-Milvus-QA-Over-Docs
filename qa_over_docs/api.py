import openai, tiktoken, json
from typing import List, TypedDict
from dotenv import load_dotenv

load_dotenv()


class ChatResponse(TypedDict):
    relevant_source_ids: List[int]
    answer: str


SYSTEM_INSTRUCTIONS = '''
Answer the user's question based on the given context.
Return your response in JSON like this:

{
    "relevant_source_ids": [],
    "answer": ...
}

where relevant_source_ids is a list of {SOURCE ID} of the corresponding source
you use to answer the user's question and answer is your response to the user's
question based on the context. For example:

{
    "relevant_source_ids": ["443350746039594436", "443350746039594128"],
    "answer": "The answer to your question is..."
}
'''


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens


def get_messages_token_length(messages: list[dict]):
    content = [i["content"] for i in messages]
    return num_tokens_from_string("\n".join(content))


def retrieve_response(question: str, relevant_docs: list[dict]) -> ChatResponse:
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "system", "content": "CONTEXT: \n\n\n\n"},
        {"role": "user", "content": f"{question}\n\nPlease remember to respond in JSON shown before"}
    ]

    base_token_length = get_messages_token_length(messages)
    max_token_length = 3700

    context = ""

    for doc in relevant_docs:
        new_context = context
        new_context += "\n\n\n" + "{SOURCE ID}: " +  str(doc["pk"]) + "\n" + doc["text"]

        if num_tokens_from_string(new_context) > max_token_length - base_token_length:
            break

        context = new_context

    messages[1]["content"] += context

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    print(completion.choices[0].message.content.strip())

    response = json.loads(completion.choices[0].message.content.strip())
    response["relevant_source_ids"] = [int(source_id) for source_id in response["relevant_source_ids"]]

    response: ChatResponse = response

    return response


if __name__ == '__main__':
    retrieve_response("")