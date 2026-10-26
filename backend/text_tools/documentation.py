from django.conf import settings
from django.http import Http404
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


class DocumentationVisibilityMixin:
    def dispatch(self, request, *args, **kwargs):
        if not settings.ENABLE_API_DOCS:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class SchemaView(DocumentationVisibilityMixin, SpectacularAPIView):
    pass


class DocsView(DocumentationVisibilityMixin, SpectacularSwaggerView):
    pass
