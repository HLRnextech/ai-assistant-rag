from marshmallow import Schema, fields, validate


def create_config_schema(partial=False):
    class CreateBotConfigurationSchema(Schema):
        secondary_color = fields.Str(
            required=not partial, validate=validate.Regexp(r'^#(?:[0-9a-fA-F]{3}){1,2}$'))
        disclaimer_message = fields.Str(
            required=not partial, validate=validate.Length(min=1, max=200))
        greeting_message = fields.Str(
            required=not partial, validate=validate.Length(min=1, max=100))
        escalation_message = fields.Str(
            required=not partial, validate=validate.Length(min=1, max=500))
        goodbye_message = fields.Str(
            required=not partial, validate=validate.Length(min=1, max=200))
        feedback_requested_message = fields.Str(
            required=not partial, validate=validate.Length(min=1, max=100))

    return CreateBotConfigurationSchema


CreateBotConfigurationSchema = create_config_schema()


class CreateBotSchema(Schema):
    client_guid = fields.Str(required=True, validate=validate.Length(equal=32))
    bot_name = fields.Str(
        required=True, validate=validate.Length(min=1, max=100))
    configuration = fields.Nested(CreateBotConfigurationSchema, required=True)
    urls = fields.List(fields.Str(), required=True, validate=validate.And(
        validate.Length(max=100, min=0),
        lambda urls: all(validate.URL(absolute=True, schemes=[
                         'http', 'https'])(url) for url in urls),
    ))
    practice_url = fields.Str(required=False, validate=validate.URL(
        absolute=True, schemes=['http', 'https']))


class EditUrlSchema(Schema):
    added = fields.List(fields.Str(), required=False, validate=validate.And(
        validate.Length(max=100, min=0),
        lambda urls: all(validate.URL(absolute=True, schemes=[
                         'http', 'https'])(url) for url in urls),
    ))

    removed = fields.List(fields.Str(), required=False, validate=lambda asset_guids: all(
        validate.Length(equal=32)(guid) for guid in asset_guids
    ))


class EditBotSchema(Schema):
    bot_name = fields.Str(
        required=False, validate=validate.Length(min=1, max=100))
    configuration = fields.Nested(
        create_config_schema(partial=True), required=False)
    urls = fields.Nested(EditUrlSchema, required=False)
    practice_url = fields.Str(required=False, validate=validate.URL(
        absolute=True, schemes=['http', 'https']))
    files_removed = fields.List(fields.Str(), required=False, validate=lambda asset_guids: all(
        validate.Length(equal=32)(guid) for guid in asset_guids
    ))
