from flask import Blueprint, jsonify, request
import traceback

from app import db
from asset.models import Asset, AssetStatus
from utils.capture_exception import capture_exception
from bot.schemas import CreateBotSchema, EditBotSchema
from validation.schemas import GuidSchema, SkipLimitSchema
from errors import CustomHTTPException
from bot.models import Bot, BotStatus, DeploymentStatus
from client.models import Client
from bot_assets.models import BotAssets
from middleware.api_key import api_key_required
from mq import mq
from utils.embed_code import generate_embed_code
import s3
from utils.logger import logger
from settings import CHATBOT_JS_ASSET_URL, CHATBOT_CSS_ASSET_URL

bot_router = Blueprint("bot", __name__, url_prefix="/bot")


@bot_router.route("/create", methods=["POST"])
@api_key_required
def create():
    # request will be form-data
    body = request.form.get("body")
    if not body:
        raise CustomHTTPException("Missing body", 400)

    parsed_body = CreateBotSchema().loads(body)
    logo = request.files.get("logo")
    files = request.files.getlist("files")

    # if logo is present, ensure it is either png or jpg or jpeg
    if logo is not None:
        if logo.filename is None or logo.filename == "":
            raise CustomHTTPException(
                "Invalid logo uploaded. Please choose a valid logo", 400)

        logger.info(
            f'logo file {logo.filename} content type: {logo.content_type}')
        if logo.content_type not in ["image/png", "image/jpeg"]:
            ex = CustomHTTPException(
                "Only png or jpg or jpeg files are allowed for logo", 400)
            capture_exception(ex, metadata={
                "logo_filename": logo.filename,
                "logo_content_type": logo.content_type
            })
            raise ex

    # if files are present, ensure all files are either pdf or doc or docx
    if files is not None and len(files) > 0:
        for file in files:
            if file.filename is None or file.filename == "":
                raise CustomHTTPException(
                    "Invalid file uploaded. Please upload a valid file", 400)

            logger.info(
                f'file {file.filename} content type: {file.content_type}')
            if file.content_type not in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                ex = CustomHTTPException(
                    "Only pdf or doc or docx files are allowed for files", 400)
                capture_exception(ex, metadata={
                    "filename": file.filename,
                    "content_type": file.content_type
                })
                raise ex

    logo_url = None
    file_urls = []
    try:
        if len(parsed_body["urls"]) == 0 and len(files) == 0 and "practice_url" not in parsed_body:
            raise CustomHTTPException(
                "At least one url or file or practice url should be provided", 400)

        client = Client.find_one_by_guid(parsed_body["client_guid"])
        if client is None:
            raise CustomHTTPException("Client not found", 404)

        if logo is not None and logo.filename is not None and logo.filename != "":
            logo_url = s3.upload_file(logo)

        if files is not None and len(files) > 0:
            for file in files:
                u = s3.upload_file(file)
                file_urls.append(u)

        bot = Bot.new_bot(body=parsed_body, client=client,
                          file_urls=file_urls, files=files, logo_url=logo_url)

        return jsonify({
            "staging_bot_guid": bot.guid,
            "staging_bot_widget": {
                "js": CHATBOT_JS_ASSET_URL,
                "css": CHATBOT_CSS_ASSET_URL
            },
            "embed_code": generate_embed_code(bot.guid)
        }), 201

    except CustomHTTPException as e:
        traceback.print_exc()
        files_to_delete = []
        if logo_url is not None:
            files_to_delete.append(logo_url)
        for file_url in file_urls:
            files_to_delete.append(file_url)

        s3.delete_files(*files_to_delete)
        raise e
    except Exception as e:
        traceback.print_exc()
        files_to_delete = []
        if logo_url is not None:
            files_to_delete.append(logo_url)
        for file_url in file_urls:
            files_to_delete.append(file_url)

        s3.delete_files(*files_to_delete)
        raise CustomHTTPException("Internal server error", 500)


@ bot_router.route("/edit/<guid>", methods=["PUT"])
@ api_key_required
def edit(guid):
    # request will be form-data
    body = request.form.get("body")
    if not body:
        body = "{}"

    parsed_body = EditBotSchema().loads(body)

    bot = Bot.find_one_by_guid(guid)
    if bot is None:
        raise CustomHTTPException("Bot not found", 404)

    if bot.status == BotStatus.FAILED:
        raise CustomHTTPException(
            "Bot is in failed state. Please remove the assets that are failing and then try again.", 400
        )

    if bot.status != BotStatus.SUCCESS:
        raise CustomHTTPException(
            f"Bot status is {bot.status.value}. Please wait for the bot to finish processing", 400)

    if bot.deployment_status != DeploymentStatus.STAGING:
        raise CustomHTTPException(
            "Edits are only allowed for staging bots", 400)

    logo = request.files.get("logo")
    files = request.files.getlist("files")

    # if logo is present, ensure it is either png or jpg or jpeg
    if logo is not None:
        if logo.filename is None or logo.filename == "":
            raise CustomHTTPException(
                "Invalid logo uploaded. Please choose a valid logo", 400)
        logger.info(
            f'logo file {logo.filename} content type: {logo.content_type}')
        if logo.content_type not in ["image/png", "image/jpeg"]:
            ex = CustomHTTPException(
                "Only png or jpg or jpeg files are allowed for logo", 400)
            capture_exception(ex, metadata={
                "logo_filename": logo.filename,
                "logo_content_type": logo.content_type
            })
            raise ex

    # if files are present, ensure all files are either pdf or doc or docx
    if files is not None and len(files) > 0:
        for file in files:
            if file.filename is None or file.filename == "":
                raise CustomHTTPException(
                    "Invalid file uploaded. Please upload a valid file", 400)

            logger.info(
                f'file {file.filename} content type: {file.content_type}')
            if file.content_type not in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                ex = CustomHTTPException(
                    "Only pdf or doc or docx files are allowed for files", 400)
                capture_exception(ex, metadata={
                    "filename": file.filename,
                    "content_type": file.content_type
                })
                raise ex

    new_logo_url = None
    existing_logo_url = bot.logo_url
    new_file_urls = []

    try:
        is_bot_queueing_required = False

        if "bot_name" in parsed_body and len(parsed_body["bot_name"]) > 0:
            if parsed_body["bot_name"] != bot.name:
                bot.name = parsed_body["bot_name"]
                bot.updated_at = db.func.now()

        # 3. if configuration is present, get all keys in config object and update the existing values in the bot configuration
        if "configuration" in parsed_body:
            existing_config = bot.configuration
            new_config = parsed_body["configuration"]

            bot.configuration = {}
            for key in existing_config.keys():
                if key in new_config:
                    bot.configuration[key] = new_config[key]
                else:
                    bot.configuration[key] = existing_config[key]

            bot.updated_at = db.func.now()

        # 4. if logo is present, upload the logo and update the logo_url in the bot
        if logo is not None and logo.filename is not None and logo.filename != "":
            new_logo_url = s3.upload_file(logo)
            existing_logo_url = bot.logo_url
            bot.logo_url = new_logo_url
            bot.updated_at = db.func.now()

        # 5. if files_removed key is present, remove the mapping b/w bot and the corresponding file assets
        if "files_removed" in parsed_body:
            assets = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
                .filter(
                BotAssets.bot_id == bot.id,
                Asset.deleted_at == None,
                Asset.type == "file",
                Asset.guid.in_(parsed_body["files_removed"]),
                BotAssets.deleted_at == None
            ).all()

            if len(assets) == 0 or len(assets) != len(parsed_body["files_removed"]):
                raise CustomHTTPException(
                    "Some files to be removed are not present in the bot. Please recheck.", 400)

            bot_assets_mapping = BotAssets.query.filter(
                BotAssets.bot_id == bot.id,
                BotAssets.asset_id.in_([asset.id for asset in assets]),
                BotAssets.deleted_at == None
            ).all()

            for ba in bot_assets_mapping:
                ba.deleted_at = db.func.now()

            bot.updated_at = db.func.now()

        # 6. if practice_url is present and is different from the current practice_url
        # update the practice_url in the bot and also mark the existing practice_url to be detached
        # i.e. remove mapping b/w bot and existing practice_url and its child urls
        # also send a message to the queue to process the new practice_url after the transaction is committed
        new_practice_url_asset = None
        if "practice_url" in parsed_body:
            existing_practice_url_asset = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
                .filter(
                BotAssets.bot_id == bot.id,
                Asset.deleted_at == None,
                Asset.type == "practice_url",
                BotAssets.deleted_at == None
            ).first()

            if existing_practice_url_asset is None or existing_practice_url_asset.value != parsed_body["practice_url"]:
                new_practice_url_asset = Asset(
                    "practice_url", parsed_body["practice_url"])
                db.session.add(new_practice_url_asset)
                db.session.flush()

                # add mapping in bot_assets table
                bot_assets = BotAssets(
                    bot_id=bot.id, asset_id=new_practice_url_asset.id)
                db.session.add(bot_assets)
                is_bot_queueing_required = True

                # remove mapping of existing practice_url and its child urls
                bot_assets_mapping = BotAssets.query.filter(
                    BotAssets.bot_id == bot.id,
                    BotAssets.asset_id == existing_practice_url_asset.id
                ).first()
                if bot_assets_mapping is not None:
                    bot_assets_mapping.deleted_at = db.func.now()

                existing_child_assets = Asset.query.filter_by(
                    parent_asset_id=existing_practice_url_asset.id, deleted_at=None).all()

                existing_bot_asset_mapping = BotAssets.query.filter(
                    BotAssets.bot_id == bot.id,
                    BotAssets.asset_id.in_(
                        [asset.id for asset in existing_child_assets]),
                    BotAssets.deleted_at == None
                ).all()

                for ba in existing_bot_asset_mapping:
                    ba.deleted_at = db.func.now()

                bot.updated_at = db.func.now()

        # if urls key is present, it will be an object containing { added, removed } keys
        added_url_assets = []
        if "urls" in parsed_body:
            if "removed" in parsed_body["urls"]:
                assets = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
                    .filter(
                    BotAssets.bot_id == bot.id,
                    Asset.deleted_at == None,
                    Asset.type == "url",
                    Asset.guid.in_(parsed_body["urls"]["removed"]),
                    Asset.parent_asset_id == None,
                    BotAssets.deleted_at == None
                ).all()

                if len(assets) == 0 or len(assets) != len(parsed_body["urls"]["removed"]):
                    raise CustomHTTPException(
                        "Some urls to be removed are not present in the bot. Please recheck.", 400)

                bot_assets_mapping = BotAssets.query.filter(
                    BotAssets.bot_id == bot.id,
                    BotAssets.asset_id.in_([asset.id for asset in assets]),
                    BotAssets.deleted_at == None
                ).all()

                for ba in bot_assets_mapping:
                    ba.deleted_at = db.func.now()

                bot.updated_at = db.func.now()

            if "added" in parsed_body["urls"]:
                # do not add urls that are already present
                existing_urls = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
                    .filter(
                    BotAssets.bot_id == bot.id,
                    Asset.deleted_at == None,
                    Asset.type == "url",
                    BotAssets.deleted_at == None
                ).all()

                existing_urls = [asset.value for asset in existing_urls]

                if len(set(parsed_body["urls"]["added"]).intersection(set(existing_urls))) > 0:
                    raise CustomHTTPException(
                        "Some urls to be added are already present in the bot. Please recheck.", 400)

                url_assets = [Asset("url", url)
                              for url in parsed_body["urls"]["added"]]
                db.session.add_all(url_assets)
                db.session.flush()
                is_bot_queueing_required = True

                added_url_assets = url_assets
                bot_assets = [BotAssets(bot_id=bot.id, asset_id=asset.id)
                              for asset in url_assets]
                db.session.add_all(bot_assets)

                bot.updated_at = db.func.now()

        # if files key is present, add the new files to the bot
        added_file_assets = []
        if len(files) > 0:
            for file in files:
                u = s3.upload_file(file)
                new_file_urls.append(u)

            file_assets = [
                Asset(
                    "file",
                    url,
                    metadata={"filename": f.filename}
                )
                for url, f in zip(new_file_urls, files)
            ]

            db.session.add_all(file_assets)
            db.session.flush()
            added_file_assets = file_assets
            is_bot_queueing_required = True

            bot_assets = [BotAssets(bot_id=bot.id, asset_id=asset.id)
                          for asset in file_assets]
            db.session.add_all(bot_assets)
            bot.updated_at = db.func.now()

        # set the bot status to be QUEUED if any assets are added
        if is_bot_queueing_required:
            bot.status = BotStatus.QUEUED

        is_deviating_from_live = bot.check_is_deviating_from_live()
        if bot.is_deviating_from_live != is_deviating_from_live:
            logger.debug(
                f"marking bot {bot.id} as {'' if is_deviating_from_live else 'not'} deviating from live")
            bot.is_deviating_from_live = is_deviating_from_live
            bot.updated_at = db.func.now()

        db.session.commit()

        for asset in added_url_assets + added_file_assets:
            mq.begin_asset_processing(asset_id=asset.id, bot_id=bot.id)

        if new_practice_url_asset is not None:
            mq.begin_practice_url_processing(
                asset_id=new_practice_url_asset.id, bot_id=bot.id)

        # make sure existing logo url is not being shared by other bots
        is_logo_url_shared = Bot.query.filter(
            Bot.logo_url == existing_logo_url,
            Bot.id != bot.id,
            Bot.deleted_at == None
        ).count() > 0

        if existing_logo_url is not None and existing_logo_url != new_logo_url and not is_logo_url_shared:
            s3.delete_files(existing_logo_url)

        # if bot queueing is not required, it means either just config changed
        # or some assets were removed. if not already "SUCCESS", need to update
        # bot's status if all assets are successful
        if not is_bot_queueing_required and bot.status == BotStatus.FAILED:
            top_level_assets = Asset.query.join(BotAssets, BotAssets.asset_id == Asset.id)\
                .filter(
                BotAssets.bot_id == bot.id,
                Asset.deleted_at == None,
                Asset.parent_asset_id == None,
                BotAssets.deleted_at == None
            ).all()

            assets_success = all(
                asset.status == AssetStatus.SUCCESS for asset in top_level_assets) \
                if len(top_level_assets) > 0 else True
            if assets_success:
                bot.status = BotStatus.SUCCESS
                db.session.commit()

        return jsonify({
            "status": bot.status.value,
            "guid": bot.guid
        })
    except CustomHTTPException as e:
        capture_exception(e, metadata={
            "bot_guid": guid,
            "body": body
        })
        traceback.print_exc()
        db.session.rollback()
        files_to_delete = []
        if new_logo_url is not None:
            files_to_delete.append(new_logo_url)
        for file_url in new_file_urls:
            files_to_delete.append(file_url)

        s3.delete_files(*files_to_delete)
        raise e
    except Exception as e:
        capture_exception(e, metadata={
            "bot_guid": guid,
            "body": body
        })
        traceback.print_exc()
        db.session.rollback()
        files_to_delete = []
        if new_logo_url is not None:
            files_to_delete.append(new_logo_url)
        for file_url in new_file_urls:
            files_to_delete.append(file_url)

        s3.delete_files(*files_to_delete)
        raise CustomHTTPException("Internal server error", 500)


@ bot_router.route("/status/<guid>", methods=["GET"])
@ api_key_required
def status(guid):
    guid_schema = GuidSchema().load({"guid": guid})

    bot = Bot.find_one_by_guid(guid_schema["guid"])
    if bot is None:
        raise CustomHTTPException("Bot not found", 404)

    return jsonify({
        "guid": bot.guid,
        "status": bot.status.value
    })


@ bot_router.route("/details_full/<guid>", methods=["GET"])
@ api_key_required
def details_full(guid):
    guid_schema = GuidSchema().load({"guid": guid})

    bot = Bot.get_details_full(guid_schema["guid"])

    if bot is None:
        raise CustomHTTPException("Bot not found", 404)

    return jsonify(bot)


@ bot_router.route("/details/<guid>", methods=["GET"])
def details(guid):
    # polling endpoint to be used by frontend
    guid_schema = GuidSchema().load({"guid": guid})

    bot = Bot.get_details_partial(guid_schema["guid"])

    if bot is None:
        raise CustomHTTPException("Bot not found", 404)

    return jsonify(bot)


@ bot_router.route("/list", methods=["GET"])
@ api_key_required
def paginate():
    skip = request.args.get("skip", 0)
    limit = request.args.get("limit", 10)
    client_guid = request.args.get("client_guid")

    skip_limit_schema = SkipLimitSchema().load({"skip": skip, "limit": limit})
    if client_guid is not None:
        guid_schema = GuidSchema().load({"guid": client_guid})
    else:
        guid_schema = {"guid": None}

    bots_data = Bot.paginate(
        skip=skip_limit_schema["skip"],
        limit=skip_limit_schema["limit"],
        client_guid=guid_schema["guid"])

    if bots_data is None:
        raise CustomHTTPException("Client not found", 404)

    return jsonify({
        "bots": bots_data[0],
        "more": bots_data[1]
    })


@ bot_router.route("/rollout/<guid>", methods=["GET"])
@ api_key_required
def rollout(guid):
    guid_schema = GuidSchema().load({"guid": guid})
    bot = Bot.find_one_by_guid(guid_schema["guid"])
    if not bot:
        raise CustomHTTPException("Bot not found", 404)

    live_bot_guid = bot.rollout_to_live()

    return jsonify({
        "success": True,
        "live_bot_guid": live_bot_guid,
        "live_bot_widget": {
            "js": CHATBOT_JS_ASSET_URL,
            "css": CHATBOT_CSS_ASSET_URL
        },
        "embed_code": generate_embed_code(live_bot_guid)
    })


@ bot_router.route("/delete/<guid>", methods=["DELETE"])
@ api_key_required
def delete(guid):
    guid_schema = GuidSchema().load({"guid": guid})
    bot = Bot.find_one_by_guid(guid_schema["guid"])
    if not bot:
        raise CustomHTTPException("Bot not found", 404)

    bot.soft_delete()
    return jsonify({
        "success": True
    })
