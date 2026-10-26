from rest_framework import serializers

from .models import TextAnalysis
from .services import OPERATIONS


class StrictTextField(serializers.CharField):
    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError("Text must be a string.")
        try:
            data.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise serializers.ValidationError("Text must contain valid Unicode.") from exc
        return super().to_internal_value(data)


class HistoryQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)


class TextInputSerializer(serializers.Serializer):
    text = StrictTextField(max_length=20_000, trim_whitespace=False)

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter some text first.")
        return value


class AnalyzeInputSerializer(TextInputSerializer):
    save = serializers.BooleanField(default=False)


class TransformInputSerializer(TextInputSerializer):
    operation = serializers.ChoiceField(choices=OPERATIONS)


class WordFrequencySerializer(serializers.Serializer):
    word = serializers.CharField()
    count = serializers.IntegerField()


class AnalysisResultSerializer(serializers.Serializer):
    word_count = serializers.IntegerField()
    character_count = serializers.IntegerField()
    characters_without_whitespace = serializers.IntegerField()
    sentence_count = serializers.IntegerField()
    paragraph_count = serializers.IntegerField()
    unique_word_count = serializers.IntegerField()
    reading_time_seconds = serializers.IntegerField()
    top_words = WordFrequencySerializer(many=True)


class AnalyzeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    saved = serializers.BooleanField()
    result = AnalysisResultSerializer()


class TransformResponseSerializer(serializers.Serializer):
    operation = serializers.CharField()
    result = serializers.CharField(allow_blank=True)


class TextAnalysisSerializer(serializers.ModelSerializer):
    result = AnalysisResultSerializer(read_only=True)

    class Meta:
        model = TextAnalysis
        fields = ["id", "text", "result", "created_at"]
        read_only_fields = fields
