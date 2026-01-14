from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class League(models.Model):
    """Liga piłkarska"""
    tournament_id = models.CharField(max_length=50, unique=True)
    tournament_template_id = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)

    class Meta:
        verbose_name = "League"
        verbose_name_plural = "Leagues"

    def __str__(self):
        return self.name


class Season(models.Model):
    """Sezon rozgrywek"""
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='seasons')
    season_id = models.IntegerField()
    name = models.CharField(max_length=100)
    tournament_stage_id = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Season"
        verbose_name_plural = "Seasons"
        unique_together = ['league', 'season_id']

    def __str__(self):
        return f"{self.league.name} - {self.name}"


class Country(models.Model):
    """Kraj"""
    country_id = models.IntegerField(unique=True, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class Team(models.Model):
    """Drużyna"""
    TEAM_CLASS_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('Y', 'Youth'),
    ]

    # Tu jest kluczowa zmiana, o którą pytał błąd: participant_id
    participant_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=100, blank=True)
    three_char_name = models.CharField(max_length=3, blank=True)
    logo = models.URLField(max_length=500, blank=True)
    slug = models.SlugField(max_length=200, unique=True)

    # Dodatkowe pola
    team_class = models.CharField(max_length=1, choices=TEAM_CLASS_CHOICES, blank=True)
    stadium_name = models.CharField(max_length=200, blank=True)
    stadium_capacity = models.IntegerField(null=True, blank=True)

    # Metadane
    details_fetched = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Team"
        verbose_name_plural = "Teams"

    def __str__(self):
        return self.name


class Player(models.Model):
    """Zawodnik"""
    POSITION_CHOICES = [
        ('Goalkeepers', 'Goalkeeper'),
        ('Defenders', 'Defender'),
        ('Midfielders', 'Midfielder'),
        ('Forwards', 'Forward'),
        ('Coach', 'Coach'),
    ]

    player_id = models.CharField(max_length=50, unique=True, primary_key=True)
    slug = models.SlugField(max_length=200)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, related_name='players')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Player"
        verbose_name_plural = "Players"
        indexes = [
            models.Index(fields=['position']),
            models.Index(fields=['last_name']),
        ]

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.last_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.last_name


class TeamSquad(models.Model):
    """Relacja zawodnik-drużyna"""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='squad_members')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='teams')

    tournament_id = models.CharField(max_length=50, blank=True)
    tournament_type = models.CharField(max_length=50, blank=True)
    jersey_number = models.CharField(max_length=3, blank=True)

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Team Squad Member"
        verbose_name_plural = "Team Squad Members"
        unique_together = ['team', 'player', 'tournament_id']
        indexes = [
            models.Index(fields=['team', 'tournament_id']),
        ]

    def __str__(self):
        return f"{self.player.full_name} - {self.team.name} (#{self.jersey_number})"


class Match(models.Model):
    """Mecz piłkarski"""
    EVENT_STAGE_CHOICES = [
        ('1', 'Scheduled'),
        ('2', 'Live'),
        ('3', 'Finished'),
        ('4', 'Postponed'),
        ('5', 'Cancelled'),
    ]

    event_id = models.CharField(max_length=50, unique=True, primary_key=True)
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='matches')
    round = models.CharField(max_length=100)

    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')

    home_event_participant_id = models.CharField(max_length=50)
    away_event_participant_id = models.CharField(max_length=50)

    start_time = models.DateTimeField()
    start_utime = models.BigIntegerField()

    event_stage = models.CharField(max_length=20, choices=EVENT_STAGE_CHOICES)
    event_stage_id = models.CharField(max_length=10)

    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    home_full_time_score = models.IntegerField(null=True, blank=True)
    away_full_time_score = models.IntegerField(null=True, blank=True)
    home_halftime_score = models.IntegerField(null=True, blank=True)
    away_halftime_score = models.IntegerField(null=True, blank=True)

    winner = models.CharField(max_length=1, null=True, blank=True)
    ft_winner = models.CharField(max_length=1, null=True, blank=True)

    has_live_centre = models.BooleanField(default=False)
    has_lineups = models.BooleanField(default=False)
    home_goal_under_review = models.IntegerField(default=0)
    away_goal_under_review = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Match"
        verbose_name_plural = "Matches"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['season', 'start_time']),
            models.Index(fields=['event_stage']),
        ]

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name} ({self.start_time.date()})"


class MatchStatistic(models.Model):
    """Statystyki meczu"""
    PERIOD_CHOICES = [
        ('match', 'Match'),
        ('1st_half', '1st Half'),
        ('2nd_half', '2nd Half'),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='statistics')
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    stat_id = models.CharField(max_length=10)
    stat_name = models.CharField(max_length=100)
    home_value = models.CharField(max_length=50)
    away_value = models.CharField(max_length=50)

    home_value_numeric = models.FloatField(null=True, blank=True)
    away_value_numeric = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Match Statistic"
        verbose_name_plural = "Match Statistics"
        unique_together = ['match', 'period', 'stat_id', 'stat_name']
        indexes = [
            models.Index(fields=['match', 'period']),
            models.Index(fields=['stat_name']),
        ]

    def __str__(self):
        return f"{self.match.event_id} - {self.period} - {self.stat_name}"

    def save(self, *args, **kwargs):
        self.home_value_numeric = self._extract_numeric(self.home_value)
        self.away_value_numeric = self._extract_numeric(self.away_value)
        super().save(*args, **kwargs)

    @staticmethod
    def _extract_numeric(value):
        if not value:
            return None
        try:
            clean_value = value.split('%')[0].split('(')[0].strip()
            return float(clean_value)
        except (ValueError, AttributeError):
            return None


class StatDefinition(models.Model):
    """Definicje statystyk"""
    stat_id = models.CharField(max_length=10, unique=True, primary_key=True)
    stat_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Stat Definition"
        verbose_name_plural = "Stat Definitions"

    def __str__(self):
        return f"{self.stat_id} - {self.stat_name}"
    
    # ... (twoje inne modele: League, Team itp.)

class NewsArticle(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    url = models.URLField(unique=True)  # Link do pełnego artykułu (unikalny)
    image_url = models.URLField(blank=True, null=True)
    published_date = models.DateTimeField()
    source_name = models.CharField(max_length=100)  # np. "Sky Sports"

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_date'] # Najnowsze na górze