from django. contrib import admin
from .models import League, Season, Team, Match, MatchStatistic, Player, Country, TeamSquad, StatDefinition

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['tournament_id', 'name', 'country']
    search_fields = ['name']

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['name', 'league', 'season_id']
    list_filter = ['league']

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'three_char_name', 'stadium_name', 'details_fetched']
    search_fields = ['name']
    list_filter = ['details_fetched']

@admin. register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'home_team', 'away_team', 'start_time', 'event_stage', 'home_score', 'away_score']
    list_filter = ['event_stage', 'season']
    search_fields = ['home_team__name', 'away_team__name']
    date_hierarchy = 'start_time'

@admin.register(MatchStatistic)
class MatchStatisticAdmin(admin.ModelAdmin):
    list_display = ['match', 'period', 'stat_name', 'home_value', 'away_value']
    list_filter = ['period', 'stat_name']

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['player_id', 'full_name', 'position', 'country']
    list_filter = ['position', 'country']
    search_fields = ['first_name', 'last_name']

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['country_id', 'name']
    search_fields = ['name']

@admin.register(TeamSquad)
class TeamSquadAdmin(admin.ModelAdmin):
    list_display = ['player', 'team', 'jersey_number', 'tournament_type']
    list_filter = ['team', 'tournament_type']

@admin.register(StatDefinition)
class StatDefinitionAdmin(admin.ModelAdmin):
    list_display = ['stat_id', 'stat_name', 'category']
    search_fields = ['stat_name']