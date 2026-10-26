from django.urls import path
from text_tools import views
from text_tools.documentation import DocsView, SchemaView

urlpatterns = [
    path("", views.workspace, name="workspace"),
    path("api/csrf/", views.csrf_token, name="csrf"),
    path("api/text/analyze/", views.AnalyzeView.as_view(), name="analyze"),
    path("api/text/transform/", views.TransformView.as_view(), name="transform"),
    path("api/text/history/", views.HistoryListView.as_view(), name="history"),
    path("api/text/history/<int:pk>/", views.HistoryDetailView.as_view(), name="history-detail"),
    path("api/health/", views.health, name="health"),
    path("api/schema/", SchemaView.as_view(), name="schema"),
    path("api/docs/", DocsView.as_view(url_name="schema"), name="docs"),
]
