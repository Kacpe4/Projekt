from django.db import models

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)
    logo = models.CharField(max_length=100)
    league = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=50)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name = 'players')
class Match(models.Model):
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    match_date = models.DateTimeField()
    home_score = models.IntegerField()
    away_score = models.IntegerField()

class MatchEvent(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=50)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    event_time = models.IntegerField()
