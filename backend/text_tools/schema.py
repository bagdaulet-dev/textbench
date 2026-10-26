from drf_spectacular.extensions import OpenApiAuthenticationExtension


class BrowserSessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "text_tools.authentication.BrowserSessionAuthentication"
    name = "csrfToken"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-CSRFToken",
            "description": (
                "Get a CSRF token from /api/csrf/ with the same cookie jar. "
                "Required for POST and DELETE."
            ),
        }
