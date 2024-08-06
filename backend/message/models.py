import uuid
import enum

from app import db

from rag.utils import get_token_count


class MessageRole(enum.Enum):
    HUMAN = "human"
    BOT = "bot"


class MessageFeedback(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

    @classmethod
    def reverse_mapping(cls):
        m = {
            item.value: item for item in cls
        }
        return m


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(32), nullable=False, unique=True, index=True)
    role = db.Column(db.Enum(MessageRole), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    # lets the client know if this msg one of the configuration messages
    cfg_type = db.Column(db.String(50), nullable=True)
    content = db.Column(db.String, nullable=False)
    feedback = db.Column(db.Enum(MessageFeedback, nullable=True))
    error = db.Column(db.String(500), nullable=True)
    cost = db.Column(db.Float, nullable=True, default=0.0)
    num_tokens = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())

    session_id = db.Column(db.Integer, db.ForeignKey(
        "session.id"), nullable=False)

    def __init__(self, mtype, content, role, session, error=None, created_at=db.func.now(), cost=0, cfg_type=None):
        self.type = mtype
        self.content = content
        self.role = role
        self.session_id = session.id
        self.guid = self.generate_guid()
        self.error = error
        self.cost = cost
        self.cfg_type = cfg_type
        num_tokens = 0

        if mtype == "text":
            num_tokens = get_token_count(content)

        self.num_tokens = num_tokens
        self.created_at = created_at

    @classmethod
    def generate_guid(cls):
        return str(uuid.uuid4().hex)

    @classmethod
    def find_one_by_guid(cls, guid):
        return cls.query.filter_by(guid=guid).first()

    def store_feedback(self, feedback):
        if feedback is not None:
            f = MessageFeedback.reverse_mapping().get(feedback)
            self.feedback = f
        else:
            self.feedback = None
        self.updated_at = db.func.now()
        db.session.commit()

    def __repr__(self):
        return f"<Message {self.content[:20]}>"
