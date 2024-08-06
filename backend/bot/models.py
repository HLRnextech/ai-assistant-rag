import traceback
from app import db
from sqlalchemy.dialects.postgresql import JSON
import enum
import uuid

from utils.capture_exception import capture_exception
from errors import CustomHTTPException
from mq import mq
import s3
from bot_assets.models import BotAssets
from asset.models import Asset
from client.models import Client

from utils.embed_code import generate_embed_code
from utils.logger import logger


class BotStatus(enum.Enum):
    QUEUED = "queued"
    PROGRESS = "progress"
    SUCCESS = "success"
    FAILED = "failed"


class DeploymentStatus(enum.Enum):
    STAGING = "staging"
    LIVE = "live"


class Bot(db.Model):
    __tablename__ = "bot"

    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    deployment_status = db.Column(db.Enum(DeploymentStatus),
                                  default=DeploymentStatus.STAGING, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, server_default=db.func.now(), server_onupdate=db.func.now())
    deployed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Enum(BotStatus),
                       default=BotStatus.QUEUED, nullable=False)
    deleted_at = db.Column(db.DateTime, index=True)
    configuration = db.Column(JSON, nullable=False)
    logo_url = db.Column(db.String(400), nullable=True)
    # indicates whether the staging version and the live versions are different
    # will always be false if deployment_status is "live"
    is_deviating_from_live = db.Column(db.Boolean, default=False)

    # self-join relationship
    # useful for obtaining the corresponding live/staging version of the bot
    associated_bot_id = db.Column(
        db.Integer, db.ForeignKey("bot.id"), nullable=True)
    # many-to-one relationship with client
    client_id = db.Column(db.Integer, db.ForeignKey(
        "client.id"), nullable=False)
    # many-to-many relationship with assets
    # assets = db.relationship(
    #     "Asset", secondary="bot_assets", back_populates="bot", lazy=True, primaryjoin="Bot.id == BotAssets.c.bot_id")

    # one-to-many relationship with sessions
    # sessions = db.relationship("Session", backref="session", lazy=True)

    def __init__(self, name, client: Client, config={}, logo_url=None):
        self.name = name
        self.guid = self.generate_guid()
        self.client_id = client.id
        self.configuration = config
        self.logo_url = logo_url

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.updated_at = db.func.now()
        db.session.commit()

        return self

    @classmethod
    def new_bot(cls, body, client, file_urls, files=None, logo_url=None):
        try:
            bot = cls(name=body["bot_name"], client=client,
                      config=body["configuration"], logo_url=logo_url)

            db.session.add(bot)
            db.session.flush()

            url_assets = [Asset("url", url) for url in body["urls"]]
            file_assets = []
            if files is not None:
                file_assets = [
                    Asset(
                        "file",
                        url,
                        metadata={"filename": f.filename}
                    )
                    for url, f in zip(file_urls, files)
                ]

            db.session.add_all(url_assets)
            db.session.add_all(file_assets)

            practice_url_asset = None
            if "practice_url" in body:
                practice_url_asset = Asset(
                    "practice_url", body["practice_url"])
                db.session.add(practice_url_asset)

            db.session.flush()

            bot_assets = [BotAssets(bot_id=bot.id, asset_id=asset.id)
                          for asset in url_assets + file_assets]
            if practice_url_asset is not None:
                bot_assets.append(
                    BotAssets(bot_id=bot.id, asset_id=practice_url_asset.id))

            db.session.add_all(bot_assets)
            db.session.commit()

            for asset in url_assets:
                mq.begin_asset_processing(asset_id=asset.id, bot_id=bot.id)

            for i in range(len(file_assets)):
                fa = file_assets[i]
                f = files[i]
                mq.begin_asset_processing(
                    asset_id=fa.id, bot_id=bot.id, mime_type=f.content_type)

            if practice_url_asset is not None:
                mq.begin_practice_url_processing(
                    asset_id=practice_url_asset.id, bot_id=bot.id)

            return bot
        except Exception as e:
            capture_exception(e, metadata={
                "client_guid": client.guid,
                "body": body
            })
            db.session.rollback()
            raise e

    def soft_delete(self):
        if self.deployment_status == DeploymentStatus.STAGING:
            raise CustomHTTPException(
                "Cannot delete bot that is in staging", 400)

        def soft_delete_bot_and_asset_mapping(bot):
            bot.deleted_at = db.func.now()
            bot_asset_mapping = BotAssets.query.filter_by(
                bot_id=bot.id, deleted_at=None).all()
            for bot_asset in bot_asset_mapping:
                bot_asset.deleted_at = db.func.now()

        soft_delete_bot_and_asset_mapping(self)

        child_bots = Bot.query.filter_by(
            associated_bot_id=self.id, deleted_at=None).all()
        for child_bot in child_bots:
            soft_delete_bot_and_asset_mapping(child_bot)

        # TODO: when do we delete assets/logos/embeddings?
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
    def get_details_full(cls, guid):
        bot = cls.query.filter_by(guid=guid, deleted_at=None)\
            .join(Client, cls.client_id == Client.id)\
            .first()

        if bot is None:
            return None

        live_bot_details = {}
        if bot.associated_bot_id and bot.deployment_status == DeploymentStatus.STAGING:
            live_bot = cls.query.filter_by(
                id=bot.associated_bot_id, deleted_at=None, deployment_status=DeploymentStatus.LIVE).first()

            live_bot_assets_in_db = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
                .filter(BotAssets.bot_id == live_bot.id, Asset.deleted_at == None, Asset.parent_asset_id == None, BotAssets.deleted_at == None)\
                .all()

            live_bot_assets = []
            for asset in live_bot_assets_in_db:
                progress = None
                if asset.type == "practice_url":
                    child_assets = Asset.query.filter_by(
                        parent_asset_id=asset.id, deleted_at=None).with_entities(Asset.id, Asset.status).all()
                    progress = {
                        "total": len(child_assets),
                        "success": len([asset for asset in child_assets if asset.status.value == "success"]),
                        "failed": len([asset for asset in child_assets if asset.status.value == "failed"]),
                        "pending": len([asset for asset in child_assets if asset.status.value == "pending"]),
                    }

                live_bot_assets.append({
                    "guid": asset.guid,
                    "type": asset.type,
                    "value": asset.value,
                    "status": asset.status.value,
                    "created_at": asset.created_at.isoformat(),
                    "progress": progress,
                    "asset_metadata": asset.asset_metadata,
                })

            if live_bot is not None:
                live_bot_details = {
                    "guid": live_bot.guid,
                    "name": live_bot.name,
                    "status": live_bot.status.value,
                    "configuration": live_bot.configuration,
                    "logo_url": live_bot.logo_url,
                    "deployment_status": live_bot.deployment_status.value,
                    "created_at": live_bot.created_at.isoformat(),
                    "updated_at": live_bot.updated_at.isoformat(),
                    "assets": live_bot_assets,
                    "embed_code": generate_embed_code(live_bot.guid),
                }

        assets_in_db = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
            .filter(BotAssets.bot_id == bot.id, Asset.deleted_at == None, Asset.parent_asset_id == None, BotAssets.deleted_at == None)\
            .all()

        assets = []
        for asset in assets_in_db:
            progress = None
            if asset.type == "practice_url":
                child_assets = Asset.query.filter_by(
                    parent_asset_id=asset.id, deleted_at=None).with_entities(Asset.id, Asset.status).all()
                progress = {
                    "total": len(child_assets),
                    "success": len([asset for asset in child_assets if asset.status.value == "success"]),
                    "failed": len([asset for asset in child_assets if asset.status.value == "failed"]),
                    "pending": len([asset for asset in child_assets if asset.status.value == "pending"]),
                }

            assets.append({
                "guid": asset.guid,
                "type": asset.type,
                "value": asset.value,
                "status": asset.status.value,
                "created_at": asset.created_at.isoformat(),
                "progress": progress,
                "asset_metadata": asset.asset_metadata,
            })

        return {
            "guid": bot.guid,
            "name": bot.name,
            "status": bot.status.value,
            "configuration": bot.configuration,
            "logo_url": bot.logo_url,
            "deployment_status": bot.deployment_status.value,
            "is_deviating_from_live": bot.is_deviating_from_live,
            "deployed_at": bot.deployed_at.isoformat() if bot.deployed_at else None,
            "created_at": bot.created_at.isoformat(),
            "updated_at": bot.updated_at.isoformat(),
            "assets": assets,
            "live_bot_details": live_bot_details,
            "client": {
                "guid": bot.client.guid,
                "name": bot.client.name,
            },
            "embed_code": generate_embed_code(bot.guid),
        }

    @classmethod
    def get_details_partial(cls, guid):
        bot = cls.query.filter_by(guid=guid, deleted_at=None).first()

        if bot is None:
            return None

        return {
            "guid": bot.guid,
            "name": bot.name,
            "status": bot.status.value,
            "deployment_status": bot.deployment_status.value,
            "configuration": bot.configuration,
            "created_at": bot.created_at.isoformat(),
            "logo_url": bot.logo_url,
        }

    @classmethod
    def paginate(cls, skip=0, limit=10, client_guid=None):
        if client_guid is not None:
            client = Client.find_one_by_guid(client_guid)
            if client is None:
                return None

        filter_by = {"deleted_at": None,
                     "deployment_status": DeploymentStatus.STAGING}
        if client_guid:
            filter_by["client_id"] = client.id

        bots = cls.query.filter_by(**filter_by)\
            .join(Client, cls.client_id == Client.id)\
            .order_by(cls.created_at.desc())\
            .offset(skip)\
            .limit(limit+1)\
            .all()

        more = len(bots) > limit
        if more:
            bots = bots[:-1]

        return [
            {
                "guid": bot.guid,
                "name": bot.name,
                "status": bot.status.value,
                "created_at": bot.created_at.isoformat(),
                "updated_at": bot.updated_at.isoformat(),
                "deployed_at": bot.deployed_at.isoformat() if bot.deployed_at else None,
                "deployed_at": bot.deployed_at.isoformat() if bot.deployed_at else None,
                "client": {
                    "guid": bot.client.guid,
                    "name": bot.client.name,
                },
                "logo_url": bot.logo_url,
                "is_deviating_from_live": bot.is_deviating_from_live,
            } for bot in bots
        ], more

    def rollout_to_live(self):
        if not self.is_deviating_from_live and self.associated_bot_id is not None:
            raise CustomHTTPException(
                "Bot is not deviating from live version. No need to rollout.", 400)

        if self.deployment_status != DeploymentStatus.STAGING:
            raise CustomHTTPException("Bot is not in staging", 400)

        if self.status != BotStatus.SUCCESS:
            raise CustomHTTPException(
                "Bot does not have status of 'success'", 400)

        current_bot_assets_mapping = BotAssets.query.filter_by(
            bot_id=self.id, deleted_at=None).all()

        if len(current_bot_assets_mapping) == 0:
            raise CustomHTTPException(
                "Bot does not have any assets associated with it", 400)

        try:
            if self.associated_bot_id is None:
                client = Client.query.filter_by(id=self.client_id).first()
                live_bot = Bot(self.name, client,
                               self.configuration, self.logo_url)
                live_bot.deployment_status = DeploymentStatus.LIVE
                live_bot.status = self.status

                db.session.add(live_bot)
                db.session.flush()

                live_bot_assets_mapping = []
                for bot_asset in current_bot_assets_mapping:
                    live_bot_assets_mapping.append(
                        BotAssets(bot_id=live_bot.id,
                                  asset_id=bot_asset.asset_id)
                    )

                db.session.add_all(live_bot_assets_mapping)
                self.deployed_at = db.func.now()
                self.associated_bot_id = live_bot.id
                self.is_deviating_from_live = False
                db.session.commit()

                return live_bot.guid
            else:
                live_bot = Bot.query.filter_by(
                    id=self.associated_bot_id).first()
                live_bot.name = self.name
                live_bot.status = self.status
                live_bot.configuration = self.configuration
                # store the live bot's logo url before updating it
                # we need to check if the logo can be deleted from the s3 bucket
                live_bot_prev_logo_url = live_bot.logo_url
                live_bot.logo_url = self.logo_url
                live_bot.updated_at = db.func.now()

                db.session.flush()

                # lock the rows of the bot_assets table that are associated with the live bot
                live_bot_assets_mapping = db.session.query(BotAssets)\
                    .with_for_update().filter_by(bot_id=live_bot.id, deleted_at=None).all()

                live_bot_assets_mapping_asset_ids = [
                    bot_asset.asset_id for bot_asset in live_bot_assets_mapping]
                current_bot_asset_ids = [
                    bot_asset.asset_id for bot_asset in current_bot_assets_mapping]

                # remove asset ids from live_bot_assets_mapping that are not associated with the current bot
                for bot_asset in live_bot_assets_mapping:
                    if bot_asset.asset_id not in current_bot_asset_ids:
                        bot_asset.deleted_at = db.func.now()
                        logger.info(
                            f"marked asset {bot_asset.asset_id} as deleted for bot {live_bot.id}")

                # add asset ids from current_bot_assets_mapping that are not associated with the live bot
                for bot_asset in current_bot_assets_mapping:
                    if bot_asset.asset_id not in live_bot_assets_mapping_asset_ids:
                        db.session.add(
                            BotAssets(bot_id=live_bot.id,
                                      asset_id=bot_asset.asset_id)
                        )
                        logger.info(
                            f"added asset {bot_asset.asset_id} for bot {live_bot.id}")

                self.deployed_at = db.func.now()
                self.is_deviating_from_live = False
                db.session.commit()

                is_logo_url_shared = self.query.filter_by(
                    logo_url=live_bot_prev_logo_url,
                    deleted_at=None
                ).count() > 0
                if live_bot_prev_logo_url is not None and not is_logo_url_shared:
                    s3.delete_files(live_bot_prev_logo_url)

                return live_bot.guid
        except Exception as e:
            capture_exception(e, metadata={
                "bot_guid": self.guid
            })
            traceback.print_exc()
            db.session.rollback()
            raise CustomHTTPException("Something went wrong", 400)

    def check_is_deviating_from_live(self):
        is_deviating_from_live = False

        if self.associated_bot_id is not None and self.deployment_status == DeploymentStatus.STAGING:
            associated_live_bot = Bot.query.filter_by(
                id=self.associated_bot_id, deployment_status=DeploymentStatus.LIVE).first()

            if associated_live_bot is not None:
                if self.configuration and associated_live_bot.configuration:
                    keys = set(self.configuration.keys()).union(
                        associated_live_bot.configuration.keys())
                    for key in keys:
                        if self.configuration.get(key) != associated_live_bot.configuration.get(key):
                            is_deviating_from_live = True
                            break

                if not is_deviating_from_live and self.logo_url != associated_live_bot.logo_url:
                    is_deviating_from_live = True

                if not is_deviating_from_live and self.name != associated_live_bot.name:
                    is_deviating_from_live = True

                if not is_deviating_from_live:
                    bot_assets = BotAssets.query.filter_by(
                        bot_id=self.id, deleted_at=None).all()

                    live_bot_assets = BotAssets.query.filter_by(
                        bot_id=associated_live_bot.id, deleted_at=None).all()

                    if len(bot_assets) != len(live_bot_assets):
                        is_deviating_from_live = True

                    if not is_deviating_from_live:
                        bot_assets = sorted(
                            bot_assets, key=lambda x: x.asset_id)
                        live_bot_assets = sorted(
                            live_bot_assets, key=lambda x: x.asset_id)

                        for ba, lba in zip(bot_assets, live_bot_assets):
                            if ba.asset_id != lba.asset_id:
                                is_deviating_from_live = True
                                break

        return is_deviating_from_live

    def __repr__(self):
        return f"<Bot {self.name[:20]}>"
