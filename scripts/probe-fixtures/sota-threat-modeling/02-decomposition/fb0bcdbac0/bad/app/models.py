from django.db import models

class Integration(models.Model):
    webhook_url = models.URLField()
