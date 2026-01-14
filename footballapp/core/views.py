from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Q, Count
from .models import Team, Match, Player, MatchStatistic
from .models import NewsArticle # Import modelu
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin


class HomePageView(View):
    def get(self, request):
        return render(request, 'core/home.html')


class MatchlistView(LoginRequiredMixin,View):
    def get(self, request):
        matches = Match.objects.all().select_related('home_team', 'away_team', 'season').order_by('-start_time')
        return render(request, 'core/matchlist.html', {'matches': matches})


class TeamListView(LoginRequiredMixin, View):
    def get(self, request):
        teams = Team.objects.all().order_by('name')
        return render(request, 'core/team_list.html', {'teams': teams})


class TeamDetailView(LoginRequiredMixin, View):
    def get(self, request, team_id):
        team = get_object_or_404(Team, participant_id=team_id)

        # Wszystkie mecze drużyny
        matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team)
        ).select_related('home_team', 'away_team').order_by('-start_time')

        # Ostatnie 5 meczów
        recent_matches = matches[:5]

        # Statystyki
        finished_matches = matches.filter(event_stage='3')
        total_matches = finished_matches.count()

        wins = sum(1 for m in finished_matches if
                   (m.home_team == team and (m.home_score or 0) > (m.away_score or 0)) or
                   (m.away_team == team and (m.away_score or 0) > (m.home_score or 0)))

        draws = sum(1 for m in finished_matches if (m.home_score or 0) == (m.away_score or 0))
        losses = total_matches - wins - draws

        goals_scored = sum(
            (m.home_score or 0) if m.home_team == team else (m.away_score or 0) for m in finished_matches)
        goals_conceded = sum(
            (m.away_score or 0) if m.home_team == team else (m.home_score or 0) for m in finished_matches)

        # Zawodnicy drużyny
        players = Player.objects.filter(teams__team=team).distinct()

        context = {
            'team': team,
            'recent_matches': recent_matches,
            'all_matches': matches,
            'players': players,
            'stats': {
                'total_matches': total_matches,
                'wins': wins,
                'draws': draws,
                'losses': losses,
                'goals_scored': goals_scored,
                'goals_conceded': goals_conceded,
            }
        }
        return render(request, 'core/team_detail.html', context)


class MatchDetailView(LoginRequiredMixin, View):
    def get(self, request, match_id):
        match = get_object_or_404(Match, event_id=match_id)

        # Head to Head - zakończone mecze
        h2h_matches = Match.objects.filter(
            Q(home_team=match.home_team, away_team=match.away_team) |
            Q(home_team=match.away_team, away_team=match.home_team),
            event_stage='3'
        ).exclude(event_id=match_id).order_by('-start_time')[:10]

        # Statystyki H2H
        home_wins = sum(1 for m in h2h_matches if
                        (m.home_team == match.home_team and (m.home_score or 0) > (m.away_score or 0)) or
                        (m.away_team == match.home_team and (m.away_score or 0) > (m.home_score or 0)))

        away_wins = sum(1 for m in h2h_matches if
                        (m.home_team == match.away_team and (m.home_score or 0) > (m.away_score or 0)) or
                        (m.away_team == match.away_team and (m.away_score or 0) > (m.home_score or 0)))

        h2h_draws = sum(1 for m in h2h_matches if (m.home_score or 0) == (m.away_score or 0))

        # Statystyki meczu
        match_stats = MatchStatistic.objects.filter(match=match).order_by('period', 'stat_id')

        context = {
            'match': match,
            'match_stats': match_stats,
            'h2h_matches': h2h_matches,
            'h2h_stats': {
                'home_wins': home_wins,
                'away_wins': away_wins,
                'draws': h2h_draws,
            }
        }
        return render(request, 'core/match_detail.html', context)


class LeagueTableView(LoginRequiredMixin, View):
    def get(self, request):
        # Pobierz wszystkie zakończone mecze
        finished_matches = Match.objects.filter(event_stage='3').select_related('home_team', 'away_team')

        # Słownik do przechowywania statystyk drużyn
        teams_stats = {}

        for match in finished_matches:
            home_score = match.home_score or 0
            away_score = match.away_score or 0

            # Inicjalizacja statystyk dla drużyn
            for team in [match.home_team, match.away_team]:
                if team.participant_id not in teams_stats:
                    teams_stats[team.participant_id] = {
                        'team': team,
                        'played': 0,
                        'wins': 0,
                        'draws': 0,
                        'losses': 0,
                        'goals_for': 0,
                        'goals_against': 0,
                        'goal_difference': 0,
                        'points': 0
                    }

            # Aktualizacja statystyk gospodarzy
            home_stats = teams_stats[match.home_team.participant_id]
            home_stats['played'] += 1
            home_stats['goals_for'] += home_score
            home_stats['goals_against'] += away_score

            # Aktualizacja statystyk gości
            away_stats = teams_stats[match.away_team.participant_id]
            away_stats['played'] += 1
            away_stats['goals_for'] += away_score
            away_stats['goals_against'] += home_score

            # Określ wynik
            if home_score > away_score:
                home_stats['wins'] += 1
                home_stats['points'] += 3
                away_stats['losses'] += 1
            elif home_score < away_score:
                away_stats['wins'] += 1
                away_stats['points'] += 3
                home_stats['losses'] += 1
            else:
                home_stats['draws'] += 1
                away_stats['draws'] += 1
                home_stats['points'] += 1
                away_stats['points'] += 1

        # Oblicz bilans bramkowy i posortuj
        table = []
        for stats in teams_stats.values():
            stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
            table.append(stats)

        # Sortowanie: punkty, bilans, bramki strzelone
        table.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

        # Dodaj pozycję w tabeli
        for idx, team_stats in enumerate(table, 1):
            team_stats['position'] = idx

        return render(request, 'core/league_table.html', {'table': table})


# --- TUTAJ BYŁ BŁĄD: TERAZ JEST POPRAWNIE (BEZ WCIĘCIA) ---

def news_list(request):
    # Pobieramy 20 najnowszych newsów
    articles = NewsArticle.objects.all()[:20]
    return render(request, 'core/news_list.html', {'articles': articles})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # TUTAJ BYŁ BŁĄD. Musi być 'core:home' zamiast 'home'
            return redirect('core:home') 
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})