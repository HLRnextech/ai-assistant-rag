import tiktoken

from settings import OPENAI_MODEL


def get_token_count(text: str, model: str = OPENAI_MODEL):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))
