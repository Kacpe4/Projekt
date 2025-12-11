from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100)
    logo = models.CharField(max_length=200)
    league = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    position = models.CharField(max_length=50)

    def __str__(self):
        return self.name