from marshmallow import Schema, fields, validate


class SkipLimitSchema(Schema):
    skip = fields.Int(missing=0, validate=validate.Range(min=0))
    limit = fields.Int(missing=10, validate=validate.Range(min=1, max=20))


class GuidSchema(Schema):
    guid = fields.Str(required=True, validate=validate.Length(equal=32))
