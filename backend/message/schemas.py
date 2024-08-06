from marshmallow import Schema, fields, validate

from .models import MessageFeedback


class MessageFeedbackSchema(Schema):
    session_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    user_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
    feedback = fields.Str(
        required=True, validate=validate.OneOf(list(MessageFeedback.reverse_mapping().keys())), allow_none=True)
    message_guid = fields.Str(
        required=True, validate=validate.Length(equal=32))
