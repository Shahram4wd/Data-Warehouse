from django.db import models

class ReportCategory(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Report(models.Model):
    category = models.ForeignKey(ReportCategory, on_delete=models.CASCADE, related_name='reports')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    query = models.TextField(help_text="SQL query or logic to generate the report")

    def __str__(self):
        return self.name
