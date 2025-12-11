from django.urls import path
from . import views

urlpatterns = [
    path('' , views.HomePageView.as_view() , name='HomePage'),
    path('matches/' , views.MatchlistView.as_view() , name='Matchlist'),
]