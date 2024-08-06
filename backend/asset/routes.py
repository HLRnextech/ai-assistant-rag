from flask import Blueprint, jsonify

from asset.models import Asset
from validation.schemas import GuidSchema
from errors import CustomHTTPException
from middleware.api_key import api_key_required


asset_router = Blueprint("asset", __name__, url_prefix="/asset")


@asset_router.route("/details/practice_url/<guid>", methods=["GET"])
@api_key_required
def practice_url_details(guid):
    guid_schema = GuidSchema().load({"guid": guid})

    asset_details = Asset.practice_url_details(guid_schema["guid"])

    if asset_details is None:
        raise CustomHTTPException("Asset not found", 404)

    return jsonify(asset_details)
