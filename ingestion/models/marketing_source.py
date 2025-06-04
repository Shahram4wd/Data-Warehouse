from django.db import models
import uuid

class MarketingSource(models.Model):
    """
    Marketing source model for tracking lead and customer acquisition channels.
    This model is separate from the Genius-specific marketing sources.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Marketing Source"
        verbose_name_plural = "Marketing Sources"
        db_table = "ingestion_marketingsource"

    def __str__(self):
        return self.name
