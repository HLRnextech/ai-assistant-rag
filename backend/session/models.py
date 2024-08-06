from datetime import datetime
import enum
import uuid
import json
import traceback


from app import db

from utils.capture_exception import capture_exception
from rag.answer import answer_question_stream
from errors import CustomHTTPException
from message.models import Message, MessageRole
from bot.models import Bot
from cache import cache
# from rag.answer import answer_question_stream


class SessionStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Session(db.Model):
    __tablename__ = "session"

    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(32), nullable=False, unique=True, index=True)
    user_guid = db.Column(db.String(32), nullable=False)
    status = db.Column(db.Enum(SessionStatus),
                       default=SessionStatus.ACTIVE, nullable=False)
    # feedback is a star rating out of 5
    feedback = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    last_active_at = db.Column(
        db.DateTime, server_default=db.func.now(), nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

    bot_id = db.Column(db.Integer, db.ForeignKey(
        "bot.id"), nullable=False)
    messages = db.relationship("Message", backref="session", lazy=True)

    def __init__(self, user_guid, bot):
        self.user_guid = user_guid
        self.bot_id = bot.id
        self.guid = self.generate_guid()

    @classmethod
    def end_session(cls, session_guid, user_guid):
        cls.query.filter_by(guid=session_guid, user_guid=user_guid, status=SessionStatus.ACTIVE)\
            .update({"status": SessionStatus.INACTIVE, "ended_at": db.func.now()})

        db.session.commit()

    @classmethod
    def generate_guid(cls):
        return str(uuid.uuid4().hex)

    @classmethod
    def find_one_by_guid(cls, guid):
        return cls.query.filter_by(guid=guid, deleted_at=None).first()

    @classmethod
    def create_session(cls, user_guid, bot):
        # allow only one session per user_guid for a bot
        existing_session = cls.query.filter_by(
            user_guid=user_guid, bot_id=bot.id, status=SessionStatus.ACTIVE).first()
        if existing_session:
            raise CustomHTTPException(
                "Session already exists. Please end the current conversation before starting a new one.", 400)

        session = cls(user_guid, bot)
        db.session.add(session)
        db.session.flush()

        bot_data = Bot.query.filter_by(id=session.bot_id).first()
        if bot_data is not None and bot_data.configuration is not None and 'greeting_message' in bot_data.configuration:
            bot_greeting_msg = Message(
                "text", bot_data.configuration['greeting_message'], MessageRole.BOT, session, cfg_type='greeting_message')
            db.session.add(bot_greeting_msg)

        db.session.commit()
        return session

    def trigger_bot_message(self, message_type):
        bot = Bot.query.get(self.bot_id)
        if bot is None:
            raise CustomHTTPException(
                "Session is invalid. Please start a new conversation.", 404)

        content = bot.configuration.get(message_type, None)
        if content is None:
            raise CustomHTTPException(
                "Something went wrong.", 404)

        message = Message("text", content, MessageRole.BOT,
                          self, cfg_type=message_type)
        db.session.add(message)
        self.last_active_at = db.func.now()
        db.session.commit()

        return message

    def answer_question_stream(self, question, ctx):
        with ctx:
            cache_key = self.cache_key()
            cache.set(cache_key, "1", ttl=30)

            user_message = Message(
                "text", question, MessageRole.HUMAN, self, created_at=datetime.now())
            db.session.add(user_message)
            ai_response = ""
            error = None
            try:
                for token in answer_question_stream(question, self):
                    ai_response += token
                    yield f"data: {json.dumps({ 'token': token })}\n\n"
            except Exception as e:
                capture_exception(e, metadata={
                    "session_guid": self.guid,
                    "user_guid": self.user_guid,
                    "question": question,
                })
                traceback.print_exc()
                error = 'Something went wrong. Please try again later.'
                if len(ai_response) == 0:
                    ai_response = 'Something went wrong. Please try again later.'
            finally:
                bot_message = Message("text", ai_response,
                                      MessageRole.BOT, self, error, created_at=datetime.now())
                db.session.add(bot_message)
                self.last_active_at = db.func.now()
                db.session.commit()
                cache.delete(cache_key)

                # TODO: send an "error" key in the response to have the UI display an error message
                yield f"data: {json.dumps({ 'bot_message_guid': bot_message.guid, 'user_message_guid': user_message.guid })}\n\n"

            return

    @classmethod
    def paginate_messages(cls, session_guid, user_guid):  # skip=0, limit=10
        session = cls.query.filter_by(
            guid=session_guid, user_guid=user_guid).first()
        if session is None:
            return None

        messages = Message.query\
            .with_entities(
                Message.guid,
                Message.type,
                Message.role,
                Message.content,
                Message.created_at,
                Message.feedback,
                Message.cfg_type
            )\
            .filter(Message.session_id == session.id)\
            .order_by(Message.created_at.asc())\
            .all()
        # .offset(skip)\
        # .limit(limit + 1)\

        # more = len(messages) > limit
        # if more:
        #     messages = messages[:-1]

        return [
            {
                "guid": msg.guid,
                "role": msg.role.value,
                "type": msg.type,
                "content": msg.content,
                "feedback": msg.feedback.value if msg.feedback is not None else None,
                "cfg_type": msg.cfg_type,
                "created_at": msg.created_at.isoformat()
            } for msg in messages
        ]
    # , more

    def store_feedback(self, feedback):
        self.feedback = feedback
        self.updated_at = db.func.now()
        db.session.commit()

    def cache_key(self):
        return f"session:{self.guid}"

    def __repr__(self):
        return f"<Session {self.guid[:20]}>"
