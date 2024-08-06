from pgvector.sqlalchemy import Vector

from app import db


class Embedding(db.Model):
    __tablename__ = "embedding"

    id = db.Column(db.Integer, primary_key=True)
    embedding = db.Column(Vector(dim=512), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    chunk_text = db.Column(db.Text, nullable=False)
    chunk_metadata = db.Column(db.JSON, nullable=True)

    # one-to-many relationship with assets
    asset_id = db.Column(db.Integer, db.ForeignKey(
        "asset.id"), nullable=False)

    def __init__(self, chunk_text, embedding, asset):
        self.chunk_text = chunk_text
        self.embedding = embedding
        self.asset_id = asset.id

    def __repr__(self):
        return f"<Embedding {self.chunk_text[:20]}>"
