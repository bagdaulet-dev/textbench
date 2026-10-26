from django.db import models


class TextAnalysis(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    text = models.TextField()
    result = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "text analyses"

    def __str__(self):
        return f"Analysis {self.pk}"
