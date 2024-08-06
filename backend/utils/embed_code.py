from settings import FLASK_ENV, CHATBOT_CSS_ASSET_URL, CHATBOT_JS_ASSET_URL


def generate_embed_code(bot_guid: str):
    if FLASK_ENV == "production":
        return f"""<!-- CSS File needs to be included in the head tag -->
<link rel="stylesheet" href="{CHATBOT_CSS_ASSET_URL}">
<!-- JS File needs to be included at the end of the body tag -->
<script data-nb-guid="{bot_guid}" src="{CHATBOT_JS_ASSET_URL}" async defer></script>"""

    return "N/A"
