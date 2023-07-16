import openai, tiktoken
from dotenv import load_dotenv

load_dotenv()

def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens

def get_messages_token_length(messages: list[dict]):
    content = [i["content"] for i in messages]
    return num_tokens_from_string("\n".join(content))

def retrieve_response(question: str, relevant_docs: list[dict]) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Answer the user's question based on the given context."},
        {"role": "system", "content": "CONTEXT: \n\n\n\n"},
        {"role": "user", "content": question}
    ]

    base_token_length = get_messages_token_length(messages)
    max_token_length = 4000

    context = ""

    for doc in relevant_docs:
        new_context = context
        new_context += "\n\n\n" + doc["text"]

        if num_tokens_from_string(new_context) > max_token_length - base_token_length:
            break

        context = new_context

    messages[1]["content"] += context

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    return completion.choices[0].message.content.strip()

if __name__ == '__main__':
    retrieve_response("")