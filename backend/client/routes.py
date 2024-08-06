from flask import Blueprint, request, jsonify

from app import db
from validation.schemas import GuidSchema, SkipLimitSchema
from middleware.api_key import api_key_required
from errors import CustomHTTPException
from client.models import Client
from client.schemas import CreateClientSchema, EditClientSchema

client_router = Blueprint("client", __name__, url_prefix="/client")


@client_router.route("/create", methods=["POST"])
@api_key_required
def create():
    req_json = request.get_json(silent=True)
    if req_json is None:
        raise CustomHTTPException("Invalid request", 400)

    client_data = CreateClientSchema().load(req_json)

    client = Client(**client_data)
    db.session.add(client)
    db.session.commit()

    return jsonify({
        "guid": client.guid
    })


@client_router.route("/list", methods=["GET"])
@api_key_required
def list_clients():
    skip = request.args.get("skip", 0)
    limit = request.args.get("limit", 10)

    pagination = SkipLimitSchema().load({
        "skip": skip,
        "limit": limit
    })

    clients, more = Client.paginate(
        skip=pagination["skip"], limit=pagination["limit"])

    return jsonify({
        "clients": clients,
        "more": more
    })


@client_router.route("/edit/<guid>", methods=["PUT"])
@api_key_required
def edit(guid):
    req_json = request.get_json(silent=True)
    if req_json is None:
        raise CustomHTTPException("Invalid request", 400)

    client_data = EditClientSchema().load(req_json)
    guid_schema = GuidSchema().load({"guid": guid})

    client = Client.find_one_by_guid(guid_schema["guid"])
    if not client:
        raise CustomHTTPException("Client not found", 404)

    # check if another client already has the same name
    existing_client = Client.find_one_by_name(client_data["name"])
    if existing_client is not None:
        raise CustomHTTPException(
            "Client with the same name already exists", 409)

    updated_client = client.update(**client_data)

    return jsonify({
        "guid": updated_client.guid
    })


@client_router.route("/delete/<guid>", methods=["DELETE"])
@api_key_required
def delete(guid):
    guid_schema = GuidSchema().load({"guid": guid})
    client = Client.find_one_by_guid(guid_schema["guid"])
    if not client:
        raise CustomHTTPException("Client not found", 404)

    # TODO: soft delete client related bots/assets/embeddings
    client.soft_delete()

    return jsonify({
        "success": True
    })
