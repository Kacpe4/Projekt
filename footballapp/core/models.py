from django.db import models

class Team(models.Model):
    name = models.CharField(max_length=100)
    # Zmiana: null=True pozwala na puste wartości w bazie
    logo = models.CharField(max_length=200, null=True, blank=True) 
    league = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

class Player(models.Model):
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    # Tu też pozwalamy na brak pozycji
    position = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f'{self.name},{self.position},{self.team}'
    
# ... (Twoje istniejące modele Team i Player są tutaj wyżej)

class Match(models.Model):
    # To jest uproszczony model Meczu (jeśli go nie masz)
    # W przyszłości dodasz tu datę, wynik itp.
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

class MatchStatistic(models.Model):
    # Łączymy statystykę z konkretnym meczem
    match = models.ForeignKey(Match, related_name='statistics', on_delete=models.CASCADE)
    
    # Okres meczu: "Match", "1st Half", "2nd Half" itd.
    period = models.CharField(max_length=50)
    
    # ID statystyki z API (np. "12")
    stat_id = models.CharField(max_length=50)
    
    # Nazwa statystyki (np. "Ball Possession")
    name = models.CharField(max_length=100)
    
    # Wartości (muszą być tekstowe, bo zawierają %, nawiasy itp.)
    home_value = models.CharField(max_length=50)
    away_value = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.match} - {self.period} - {self.name}"
