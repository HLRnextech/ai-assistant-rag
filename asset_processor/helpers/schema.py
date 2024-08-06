from marshmallow import Schema, fields, validate


class InputMessageSchema(Schema):
    asset_id = fields.Int(required=True, valudate=validate.Range(min=1))
    bot_id = fields.Int(required=True, valudate=validate.Range(min=1))
    mime_type = fields.Str(required=False)
