import re

from app import db, create_app

from openai import OpenAI
import pandas.io.sql as sqlio

from message.models import Message, MessageRole
from bot.models import Bot
from settings import (
    OPENAI_API_KEY,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_MODEL,
    OPENAI_EMBEDDINGS_DIMS
)
from rag.config import (
    CHUNK_SIZE_TOKENS,
    MAX_CHUNKS_ALLOWED,
    MAX_CONTEXT_WINDOW,
    MAX_CURR_CTX_PERCENT,
    MAX_PREV_CTX_PERCENT,
    MAX_PREV_MSGS,
    get_system_prompt
)

from rag.utils import get_token_count
from utils.logger import logger, set_prefix


# TODO: implement cost calculation
def answer_question_stream(question: str, session):
    global logger
    logger = set_prefix(logger, f"session={session.guid}")
    _app = create_app(bare=True)

    with _app.app_context():
        max_context_window = MAX_CONTEXT_WINDOW[OPENAI_MODEL]
        curr_input_ctx_window = int(max_context_window * MAX_CURR_CTX_PERCENT)
        num_chunks = min(curr_input_ctx_window //
                         CHUNK_SIZE_TOKENS, MAX_CHUNKS_ALLOWED)
        prev_input_ctx_window = int(max_context_window * MAX_PREV_CTX_PERCENT)

        bot = Bot.query.filter_by(id=session.bot_id).first()
        if bot is None:
            raise Exception(
                "Session is invalid. Please start a new conversation.")

        escalation_message = bot.configuration.get(
            'escalation_message', 'I am sorry, I am not able to help with that.')
        system_prompt = get_system_prompt(escalation_message)

        previous_messages = Message.query.filter_by(session_id=session.id)\
            .order_by(Message.created_at.desc()).limit(MAX_PREV_MSGS).all()

        previous_messages = list(reversed(previous_messages))

        if len(previous_messages) > 0:
            system_prompt += (
                '\nYou will be provided with historical conversation between you and the user. '
                'If relevant, use this to move the conversation forward'
            )

        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
        prev_msg_tokens = get_token_count(system_prompt)

        for i in range(0, len(previous_messages)):
            if prev_msg_tokens < prev_input_ctx_window and len(messages) < MAX_PREV_MSGS:
                messages.append({
                    "role": "user" if previous_messages[i].role == MessageRole.HUMAN else "assistant",
                    "content": previous_messages[i].content
                })
                prev_msg_tokens += get_token_count(
                    previous_messages[i].content, OPENAI_MODEL)
            else:
                break

        # query the database to get the matching docs
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        query_embedding = openai_client.embeddings.create(
            input=[question.replace("\n", " ")],
            model=OPENAI_EMBEDDING_MODEL,
            dimensions=OPENAI_EMBEDDINGS_DIMS
        ).data[0].embedding

        query = f'''
            SELECT e.*
            FROM embedding e JOIN bot_assets ba ON ba.asset_id = e.asset_id
            WHERE ba.bot_id = {session.bot_id}
            AND ba.deleted_at IS NULL
            ORDER BY
                e.embedding <-> '[{','.join([str(x) for x in query_embedding])}]'
            LIMIT {num_chunks};
            '''
        relevant_chunks = sqlio.read_sql_query(query, db.session.connection())
        relevant_chunks = relevant_chunks.reset_index(drop=True)

        if relevant_chunks.empty:
            yield escalation_message
            return

        logger.info(
            f"included the last {len(messages) - 1} messages from the conversation")

        main_content = f"The user's question is: {question}\nHere is the relevant information you need to analyse to get the answer:\n\n"

        for chunk in relevant_chunks['chunk_text']:
            main_content += chunk + "\n\n"

        main_content = re.sub(r'\n{2,}', '\n', main_content)
        main_content = main_content.strip()

        if len(previous_messages) > 0:
            main_content += "\nYou can also refer to the previous conversation to get more context."

        main_content += "\nProvide answer in plain text (no markdown).\n\nAnswer: "

        tokens = get_token_count(main_content, OPENAI_MODEL)
        logger.debug(f"for {OPENAI_MODEL}, user message tokens: {tokens}")

        ai_response = ""
        messages.append({
            "role": "user",
            "content": main_content
        })

        stream = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            ai_response += token
            yield token
