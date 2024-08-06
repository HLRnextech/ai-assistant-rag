# has to be the same as asset_processor/.env
CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 64

# taken from: https://platform.openai.com/docs/models/gpt-4-and-gpt-4-turbo
MAX_CONTEXT_WINDOW = {
    'gpt-3.5-turbo': 16385,
    'gpt-4': 8192,
    # 128k context window gives bad results due to lot of noise
    'gpt-4-turbo-preview': 16385,  # 128000
    'gpt-4o': 16385
}


def get_system_prompt(escalation_message: str):
    SYSTEM_PROMPT = ('You are a helpful and understanding chatbot. You have to resolve customer queries. '
                     'You will have to provide answers from the information that will be given to you. '
                     'You must understand the user\'s question, infer their intent and provide the most '
                     'relevant answer. However, If the answer is not included in the information you get, '
                     f'say exactly "{escalation_message}" and stop after that. Refuse to answer any '
                     'question that is not provided in the information you get. '
                     'Never break character. Provide output in plain text, not markdown.')

    return SYSTEM_PROMPT


# reserve 50% of the tokens for the current context
MAX_CURR_CTX_PERCENT = 0.5
# reserve 30% for the previous messages (including system prompt)
MAX_PREV_CTX_PERCENT = 0.3
# how many previous messages in the conversation to include (including system prompt)
MAX_PREV_MSGS = 10
# how many maximum chunks to forward to the model
MAX_CHUNKS_ALLOWED = 10
