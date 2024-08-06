from marshmallow import Schema, fields, validate


class CreateSessionSchema(Schema):
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))
    bot_guid = fields.Str(required=True, validate=validate.Length(equal=32))


class TriggerBotMessageSchema(Schema):
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    message_type = fields.Str(required=True, validate=validate.OneOf(
        ["goodbye_message", "feedback_requested_message"]))


class AnswerQuestionSchema(Schema):
    question = fields.Str(
        required=True, validate=validate.Length(min=1, max=500))
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))


class EndSessionSchema(Schema):
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))


class SessionStatusSchema(Schema):
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))


class ListMessagesSchema(Schema):  # SkipLimitSchema
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))


class SessionFeedbackSchema(Schema):
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    user_guid = fields.Str(required=True, validate=validate.Length(equal=32))
    feedback = fields.Int(
        required=True, validate=validate.Range(min=1, max=5), allow_none=True)
