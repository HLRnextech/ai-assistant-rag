from marshmallow import Schema, fields, validate


class CreateClientSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=5, max=200))


class EditClientSchema(CreateClientSchema):
    pass
