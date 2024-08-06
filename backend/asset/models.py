import uuid
import enum

from app import db

# import needed to sync with db
import bot_assets.models
import embedding.models


class AssetStatus(enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Asset(db.Model):
    __tablename__ = "asset"

    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(32), nullable=False, unique=True, index=True)
    type = db.Column(db.String(200), nullable=False)
    value = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    deleted_at = db.Column(db.DateTime, index=True)
    status = db.Column(db.Enum(AssetStatus),
                       default=AssetStatus.PENDING, nullable=False)
    asset_metadata = db.Column(db.JSON, nullable=True)

    # many-to-one relationship with asset (a sitemap/practice url can have multiple child urls)
    parent_asset_id = db.Column(db.Integer, db.ForeignKey(
        'asset.id'), nullable=True, default=None)

    # many-to-many relationship with bots
    # bots = db.relationship(
    #     "Bot", secondary=BotAssets, back_populates="asset", lazy=True, primaryjoin=id == BotAssets.c.asset_id)

    def __init__(self, type: str, value: str, metadata=None, parent_asset_id: int = None):
        self.value = value
        self.type = type
        self.parent_asset_id = parent_asset_id
        if metadata is not None:
            # metadata is a dictionary, and we need to escape single quotes from keys and values
            for k, v in metadata.items():
                if isinstance(k, str):
                    k = k.replace("'", "''")
                if isinstance(v, str):
                    v = v.replace("'", "''")
                metadata[k] = v

        self.asset_metadata = metadata
        self.guid = self.generate_guid()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.updated_at = db.func.now()
        db.session.commit()

        return self

    def soft_delete(self):
        self.deleted_at = db.func.now()
        db.session.commit()

    @classmethod
    def generate_guid(cls):
        return str(uuid.uuid4().hex)

    @classmethod
    def practice_url_details(cls, guid):
        practice_url_asset = cls.query.filter_by(
            guid=guid, type="practice_url", deleted_at=None).first()

        if practice_url_asset is None:
            return None

        child_urls = cls.query.filter_by(
            parent_asset_id=practice_url_asset.id).all()

        return {
            "practice_url": {
                "guid": practice_url_asset.guid,
                "value": practice_url_asset.value,
                "status": practice_url_asset.status.value,
                "created_at": practice_url_asset.created_at.isoformat(),
                "asset_metadata": practice_url_asset.asset_metadata
            },
            "child_urls": [
                {
                    "guid": child_url.guid,
                    "value": child_url.value,
                    "status": child_url.status.value,
                    "created_at": child_url.created_at.isoformat(),
                    "asset_metadata": child_url.asset_metadata
                } for child_url in child_urls
            ]
        }

    def __repr__(self):
        return f"<Asset {self.value[:20]}>"
