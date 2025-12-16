from django.urls import path
from .views import HomePageView, MatchlistView, TeamListView, TeamDetailView, MatchDetailView, LeagueTableView

app_name = 'core'

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('matches/', MatchlistView.as_view(), name='matchlist'),
    path('teams/', TeamListView.as_view(), name='team_list'),
    path('teams/<str:team_id>/', TeamDetailView.as_view(), name='team_detail'),
    path('matches/<str:match_id>/', MatchDetailView.as_view(), name='match_detail'),
    path('table/', LeagueTableView.as_view(), name='league_table'),
]
