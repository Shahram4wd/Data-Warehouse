from django.db import models

class SyncTracker(models.Model):
    """
    Tracks the last synchronization time for various data sources.
    Used by both Genius and Hubspot sync processes.
    """
    object_name = models.CharField(max_length=255, unique=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.object_name}: {self.last_synced_at}"
