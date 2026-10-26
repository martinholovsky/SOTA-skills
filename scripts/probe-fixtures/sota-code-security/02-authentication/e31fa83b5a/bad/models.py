class Profile(models.Model):
    security_question = models.CharField(max_length=200)
    security_answer = models.CharField(max_length=200)
