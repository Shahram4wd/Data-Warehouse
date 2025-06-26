from django.db import models

class ReportCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Report(models.Model):
    id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(ReportCategory, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title
