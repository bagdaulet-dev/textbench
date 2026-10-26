"""Small response policy shared by success and error responses."""


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        script_sources = "'self'"
        style_sources = "'self'"
        # Swagger uses inline initialization and pinned-domain hosted assets.
        # Documentation is disabled by default outside local development.
        if request.path == "/api/docs/":
            script_sources += " 'unsafe-inline' https://cdn.jsdelivr.net"
            style_sources += " 'unsafe-inline' https://cdn.jsdelivr.net"
        response["Content-Security-Policy"] = (
            f"default-src 'self'; script-src {script_sources}; style-src {style_sources}; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.path == "/" or request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        return response
