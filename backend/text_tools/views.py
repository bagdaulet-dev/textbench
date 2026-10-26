import logging

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TextAnalysis
from .serializers import (
    AnalyzeInputSerializer,
    AnalyzeResponseSerializer,
    HistoryQuerySerializer,
    TextAnalysisSerializer,
    TransformInputSerializer,
    TransformResponseSerializer,
)
from .services import analyze_text, transform_text

logger = logging.getLogger(__name__)


@require_GET
@ensure_csrf_cookie
def workspace(request):
    return render(request, "index.html", {"docs_enabled": settings.ENABLE_API_DOCS})


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        logger.warning("Database health check failed")
        return JsonResponse({"status": "unavailable", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})


class AnalyzeView(APIView):
    @extend_schema(request=AnalyzeInputSerializer, responses={200: AnalyzeResponseSerializer})
    def post(self, request):
        serializer = AnalyzeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"]
        result = analyze_text(text)
        analysis = None
        if serializer.validated_data["save"]:
            # Reading session data validates expiry; session_key alone does not.
            if not request.session.get("history_enabled", False):
                request.session["history_enabled"] = True
                request.session.save()
            analysis = TextAnalysis.objects.create(
                session_key=request.session.session_key, text=text, result=result
            )
        response = Response(
            {
                "id": analysis.pk if analysis else None,
                "saved": analysis is not None,
                "result": result,
            }
        )
        response["Cache-Control"] = "no-store"
        return response


class TransformView(APIView):
    @extend_schema(request=TransformInputSerializer, responses=TransformResponseSerializer)
    def post(self, request):
        serializer = TransformInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        operation = serializer.validated_data["operation"]
        response = Response(
            {
                "operation": operation,
                "result": transform_text(serializer.validated_data["text"], operation),
            }
        )
        response["Cache-Control"] = "no-store"
        return response


class SessionHistoryMixin:
    serializer_class = TextAnalysisSerializer

    def get_queryset(self):
        if not self.request.session.get("history_enabled", False):
            return TextAnalysis.objects.none()
        return TextAnalysis.objects.filter(session_key=self.request.session.session_key)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class HistoryListView(SessionHistoryMixin, generics.ListAPIView):
    """Search this browser's saved analyses, or delete its entire history."""

    @extend_schema(
        parameters=[
            OpenApiParameter("search", str, description="Text to find; at most 100 characters.")
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        query = HistoryQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        search = query.validated_data.get("search", "")
        return queryset.filter(text__icontains=search) if search else queryset

    @extend_schema(operation_id="text_history_clear", responses={204: None})
    def delete(self, request, *args, **kwargs):
        # Deliberately ignores search and pagination: this clears ALL owned rows.
        SessionHistoryMixin.get_queryset(self).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class HistoryDetailView(SessionHistoryMixin, generics.RetrieveDestroyAPIView):
    """Restore or permanently delete one analysis belonging to this browser."""

    def delete(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
