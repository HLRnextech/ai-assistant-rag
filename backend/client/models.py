from app import db
import uuid


class Client(db.Model):
    __tablename__ = "client"

    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False, unique=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    deleted_at = db.Column(db.DateTime, index=True)

    bots = db.relationship("Bot", backref="client", lazy=True)

    __table_args__ = (
        db.Index("ix_client_name_deleted_at", "name", "deleted_at"),
        db.Index("ix_client_guid_deleted_at", "guid", "deleted_at")
    )

    def __init__(self, name):
        self.name = name
        self.guid = self.generate_guid()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.updated_at = db.func.now()
        db.session.commit()

        return self

    def soft_delete(self):
        # TODO: soft delete client related bots/assets/embeddings
        self.deleted_at = db.func.now()
        db.session.commit()

    @classmethod
    def generate_guid(cls):
        return str(uuid.uuid4().hex)

    @classmethod
    def find_one_by_name(cls, name):
        return cls.query.filter_by(name=name, deleted_at=None).first()

    @classmethod
    def find_one_by_guid(cls, guid):
        return cls.query.filter_by(guid=guid, deleted_at=None).first()

    @classmethod
    def paginate(cls, skip=0, limit=10):
        clients = cls.query\
            .with_entities(cls.name, cls.guid, cls.created_at, cls.updated_at)\
            .filter(cls.deleted_at.is_(None))\
            .order_by(cls.created_at.desc())\
            .offset(skip)\
            .limit(limit + 1)\
            .all()

        more = len(clients) > limit
        if more:
            clients = clients[:-1]

        return [
            {
                "name": client.name,
                "guid": client.guid,
                "created_at": client.created_at.isoformat(),
                "updated_at": client.updated_at.isoformat()
            } for client in clients
        ], more

    def __repr__(self):
        return f"<Client {self.name[:20]}>"
