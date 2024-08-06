from flask import Blueprint, current_app, jsonify, request, Response
from urllib.parse import unquote

from bot.models import Bot, BotStatus
from errors import CustomHTTPException
from session.schemas import (
    CreateSessionSchema,
    AnswerQuestionSchema,
    EndSessionSchema,
    ListMessagesSchema,
    SessionStatusSchema,
    SessionFeedbackSchema,
    TriggerBotMessageSchema
)
from message.schemas import MessageFeedbackSchema
from session.models import Session, SessionStatus
from message.models import Message, MessageRole
from middleware.rate_limit import session_user_ratelimiter, ip_ratelimter
from cache import cache

session_router = Blueprint("session", __name__, url_prefix="/session")


@session_router.route("/create", methods=["POST"])
@ip_ratelimter.limit("30 per minute")
def create_session():
    req_json = request.get_json(silent=True)
    if req_json is None or type(req_json) is not dict:
        raise CustomHTTPException("Invalid request", 400)

    create_session_data = CreateSessionSchema().load({
        "user_guid": req_json.get("user_guid"),
        "bot_guid": req_json.get("bot_guid")
    })

    bot = Bot.find_one_by_guid(create_session_data["bot_guid"])
    if bot is None:
        raise CustomHTTPException("Bot not found", 404)

    if bot.status != BotStatus.SUCCESS:
        raise CustomHTTPException("Bot is not ready", 400)

    session = Session.create_session(create_session_data["user_guid"], bot)

    return jsonify({
        "guid": session.guid
    }), 201


@session_router.route("/trigger_bot_message/<session_guid>", methods=["POST"])
@session_user_ratelimiter.limit("30 per minute")
def trigger_bot_message(session_guid):
    req_json = request.get_json(silent=True)
    if req_json is None or type(req_json) is not dict:
        raise CustomHTTPException("Invalid request", 400)

    trigger_bot_message_data = TriggerBotMessageSchema().load({
        "user_guid": req_json.get("user_guid"),
        "message_type": req_json.get("message_type"),
        "session_guid": session_guid
    })

    session = Session.query.filter_by(
        guid=trigger_bot_message_data["session_guid"],
        user_guid=trigger_bot_message_data["user_guid"],
        status=SessionStatus.ACTIVE
    ).first()

    if session is None:
        raise CustomHTTPException(
            "Session not found. Please start a new conversation.", 404)

    message = session.trigger_bot_message(
        trigger_bot_message_data["message_type"])

    return jsonify({
        "guid": message.guid,
        "role": message.role.value,
        "type": message.type,
        "content": message.content,
        "cfg_type": message.cfg_type,
        "feedback": message.feedback,
        "created_at": message.created_at
    }), 201


@session_router.route("/answer_question/<session_guid>", methods=["GET"])
@session_user_ratelimiter.limit("1 per second")
def answer_question(session_guid):
    answer_question_data = AnswerQuestionSchema().load({
        "question": unquote(request.args.get("question", "")),
        "session_guid": session_guid,
        "user_guid": request.args.get("user_guid")
    })

    session = Session.query.filter_by(
        guid=answer_question_data["session_guid"],
        user_guid=answer_question_data["user_guid"]
    ).first()

    if session is None:
        raise CustomHTTPException(
            "Session not found. Please start a new conversation.", 404)

    if session.status == SessionStatus.INACTIVE:
        raise CustomHTTPException(
            "Session is inactive. Please start a new conversation.", 400)

    cache_key = session.cache_key()
    if cache.get(cache_key) is not None:
        raise CustomHTTPException(
            "Session is busy. Please try again in sometime.", 400)

    with current_app.app_context() as ctx:
        return Response(session.answer_question_stream(answer_question_data["question"], ctx), content_type='text/event-stream')


@session_router.route("/end/<session_guid>", methods=["DELETE"])
@session_user_ratelimiter.limit("30 per minute")
def end_session(session_guid):
    j = request.get_json(silent=True)
    if j is None or type(j) is not dict:
        raise CustomHTTPException("Invalid request", 400)

    end_session_data = EndSessionSchema().load(
        {"session_guid": session_guid, "user_guid": j.get("user_guid")})

    Session.end_session(session_guid=end_session_data["session_guid"],
                        user_guid=end_session_data["user_guid"])

    return jsonify({
        "success": True
    })


@session_router.route("/status/<session_guid>", methods=["GET"])
@session_user_ratelimiter.limit("300 per minute")
def session_status(session_guid):
    session_status_data = SessionStatusSchema().load({
        "session_guid": session_guid,
        "user_guid": request.args.get("user_guid")
    })
    session = Session.query.filter_by(
        guid=session_status_data["session_guid"],
        user_guid=session_status_data["user_guid"]
    ).first()

    if session is None:
        raise CustomHTTPException("Session not found", 404)

    return jsonify({
        "status": session.status.value,
        "feedback": session.feedback,
    })


@session_router.route("/list_messages/<session_guid>", methods=["GET"])
@session_user_ratelimiter.limit("300 per minute")
def list_messages(session_guid):
    # skip = request.args.get("skip", 0)
    # limit = request.args.get("limit", 10)

    list_messages_data = ListMessagesSchema().load({
        "session_guid": session_guid,
        # "skip": skip,
        # "limit": limit,
        "user_guid": request.args.get("user_guid")
    })

    msgs_data = Session.paginate_messages(**list_messages_data)

    if msgs_data is None:
        raise CustomHTTPException("Session not found", 404)

    return jsonify({
        "messages": msgs_data
        # "messages": msgs_data[0],
        # "more": msgs_data[1]
    })


@session_router.route("/feedback/<session_guid>/message/<message_guid>", methods=["POST"])
@session_user_ratelimiter.limit("30 per minute")
def message_feedback(session_guid, message_guid):
    j = request.get_json(silent=True)
    if j is None or type(j) is not dict:
        raise CustomHTTPException("Invalid request", 400)

    message_data = MessageFeedbackSchema().load({
        "message_guid": message_guid,
        "session_guid": session_guid,
        "feedback": j.get("feedback"),
        "user_guid": j.get("user_guid")
    })

    # ensure session and user exist
    session = Session.query.filter_by(
        guid=message_data["session_guid"],
        user_guid=message_data["user_guid"]
    ).first()
    if session is None:
        raise CustomHTTPException("Session not found", 404)

    message = Message.find_one_by_guid(message_data["message_guid"])

    if message is None:
        raise CustomHTTPException("Message not found", 404)

    if message.role != MessageRole.BOT:
        raise CustomHTTPException("Invalid request", 400)

    message.store_feedback(message_data["feedback"])

    return jsonify({
        "success": True
    })


@session_router.route("/feedback/<session_guid>", methods=["POST"])
@session_user_ratelimiter.limit("30 per minute")
def session_feedback(session_guid):
    j = request.get_json(silent=True)
    if j is None or type(j) is not dict:
        raise CustomHTTPException("Invalid request", 400)

    session_feedback_data = SessionFeedbackSchema().load({
        "session_guid": session_guid,
        "feedback": j.get("feedback"),
        "user_guid": j.get("user_guid")
    })

    session = Session.query.filter_by(
        guid=session_feedback_data["session_guid"],
        user_guid=session_feedback_data["user_guid"]
    ).first()
    if session is None:
        raise CustomHTTPException("Session not found", 404)

    session.store_feedback(session_feedback_data["feedback"])

    return jsonify({
        "success": True
    })
