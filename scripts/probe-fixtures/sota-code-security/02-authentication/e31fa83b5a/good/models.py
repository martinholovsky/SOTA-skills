class Profile(models.Model):
    recovery_codes = models.JSONField(default=list)  # hashed, single-use
