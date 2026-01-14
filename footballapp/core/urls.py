from django.urls import path
from .views import (HomePageView, MatchlistView, TeamListView, TeamDetailView,
                    MatchDetailView, LeagueTableView, SeasonsByLeagueView,
                    LeagueTablePartialView, MatchPredictionView,
                    PredictSpecificMatchView, PredictCustomMatchView,news_list)

app_name = 'core'

urlpatterns = [
    # Strona główna (zostawiamy tylko jedną wersję!)
    path('', HomePageView.as_view(), name='home'),

    # Mecze
    path('matches/', MatchlistView.as_view(), name='matchlist'),
    

    # Drużyny
    path('teams/', TeamListView.as_view(), name='team_list'),
    path('teams/<str:team_id>/', TeamDetailView.as_view(), name='team_detail'),
    path('matches/<str:match_id>/', MatchDetailView.as_view(), name='match_detail'),
    path('leagues/table/', LeagueTableView.as_view(), name='league_table'),
    path('leagues/<str:league_id>/table/', LeagueTableView.as_view(), name='league_table_by_league'),
    path('leagues/<str:league_id>/table/partial/', LeagueTablePartialView.as_view(), name='league_table_partial'),
    path('api/leagues/<str:league_id>/seasons/', SeasonsByLeagueView.as_view(), name='api_seasons_by_league'),
    # Przewidywania wyników meczów
    path('predictions/', MatchPredictionView.as_view(), name='match_predictions'),
    path('predictions/match/<str:match_id>/', PredictSpecificMatchView.as_view(), name='predict_match'),
    path('predictions/custom/', PredictCustomMatchView.as_view(), name='predict_custom'),
    path('news/', news_list, name='news_list'),
]
