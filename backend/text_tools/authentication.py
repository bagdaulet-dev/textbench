from rest_framework.authentication import SessionAuthentication


class BrowserSessionAuthentication(SessionAuthentication):
    """Enforce CSRF on unsafe requests, including anonymous browser sessions."""

    def authenticate(self, request):
        self.enforce_csrf(request)
        return None
