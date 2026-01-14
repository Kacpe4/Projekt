from django.urls import path
# Importujemy konkretne widoki jeden po drugim
from .views import (
    HomePageView,
    MatchlistView,
    TeamListView,
    TeamDetailView,
    MatchDetailView,
    LeagueTableView,
    news_list  # <--- Nasz nowy widok newsów
)

app_name = 'core'

urlpatterns = [
    # Strona główna (zostawiamy tylko jedną wersję!)
    path('', HomePageView.as_view(), name='home'),

    # Mecze
    path('matches/', MatchlistView.as_view(), name='matchlist'),
    path('matches/<str:match_id>/', MatchDetailView.as_view(), name='match_detail'),

    # Drużyny
    path('teams/', TeamListView.as_view(), name='team_list'),
    path('teams/<str:team_id>/', TeamDetailView.as_view(), name='team_detail'),

    # Tabela
    path('table/', LeagueTableView.as_view(), name='league_table'),
    
    # Newsy (bez 'views.', po prostu nazwa funkcji)
    path('news/', news_list, name='news_list'),
]