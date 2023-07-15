import openai
from dotenv import load_dotenv

load_dotenv()

def retrieve_response(user_input: str) -> str:
    return "OpenAI Example Message"

if __name__ == '__main__':
    retrieve_response("")