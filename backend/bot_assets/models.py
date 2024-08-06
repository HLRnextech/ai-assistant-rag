from app import db

from sqlalchemy import UniqueConstraint


class BotAssets(db.Model):
    # many-to-many relationship table
    __tablename__ = 'bot_assets'
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    deleted_at = db.Column(db.DateTime, nullable=True)

    # ensure unique constraint on bot_id and asset_id
    __table_args__ = (UniqueConstraint(
        'bot_id', 'asset_id', name='_bot_asset_uc'),)

    def __init__(self, bot_id, asset_id):
        self.bot_id = bot_id
        self.asset_id = asset_id
