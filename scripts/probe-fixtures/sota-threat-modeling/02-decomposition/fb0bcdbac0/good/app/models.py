from django.db import models

class Integration(models.Model):
    name = models.CharField(max_length=80)
    enabled = models.BooleanField(default=False)
