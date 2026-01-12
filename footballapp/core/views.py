from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Q, Count
from .models import Team, Match, Player, MatchStatistic, Season, League
from collections import OrderedDict

IMPORTANT_STATS = [
    'Ball Possession',
    'Expected Goals (xG)',
    'Shots on target',
    'Total shots',
    'Passes',
    'Fouls',
    'Corner Kicks',
    'Tackles',
    'Yellow Cards',
    'Red Cards',
]

class HomePageView(View):
    def get(self, request):
        return render(request, 'core/home.html')


class MatchlistView(View):
    def get(self, request):
        matches = Match.objects.all().select_related('home_team', 'away_team', 'season').order_by('-start_time')
        return render(request, 'core/matchlist.html', {'matches': matches})


class TeamListView(View):
    def get(self, request):
        teams = Team.objects.all().order_by('name')
        return render(request, 'core/team_list.html', {'teams': teams})


class TeamDetailView(View):
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
        players = (
            Player.objects
            .filter(teams__team=team)
            .prefetch_related('teams')  # prefetch, zmniejsza liczbę zapytań
            .order_by('position', 'first_name', 'last_name')  # konieczne dla poprawnego regroup
            .distinct()  # usuwa powtarzające się wiersze z JOIN
        )
        IMPORTANT_STATS = [
            'Ball Possession',
            'Expected Goals (xG)',
            'Shots on target',
            'Total shots',
            'Passes',
            'Fouls',
            'Corner Kicks',
            'Tackles',
            'Yellow Cards',
            'Red Cards',
        ]

        # pobierz ostatnie mecze (np. 10) i prefetch statistics, home/away
        matches_qs = (
            Match.objects
            .filter(Q(home_team=team) | Q(away_team=team))
            .order_by('-start_time')
            .prefetch_related('statistics', 'home_team', 'away_team')
        )
        recent_ten_matches = list(matches_qs[:10])  # konwertujemy do listy, żeby móc użyć |length w szablonie

        # zliczanie i obliczenie średnich
        totals = OrderedDict((name, {'sum': 0.0, 'count': 0}) for name in IMPORTANT_STATS)

        for match in recent_matches:
            is_home = (match.home_team_id == team.participant_id)
            for stat in match.statistics.all():
                if stat.stat_name in totals:
                    val = stat.home_value_numeric if is_home else stat.away_value_numeric
                    if val is not None:
                        totals[stat.stat_name]['sum'] += val
                        totals[stat.stat_name]['count'] += 1

        avg_stats = []
        for name, data in totals.items():
            avg = (data['sum'] / data['count']) if data['count'] else None
            avg_stats.append((name, avg))

        context = {
            'team': team,
            'recent_matches': recent_matches,
            'all_matches': matches,
            'players': players,
            'avg_stats': avg_stats,
            'recent_ten_matches': recent_ten_matches,
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


class MatchDetailView(View):
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


# python
from django.http import Http404

class LeagueTableView(View):
    def get(self, request, league_id=None):
        # Rozpoznaj ligę: najpierw tournament_id, potem tournament_template_id, potem pk
        league = None
        if league_id:
            league = League.objects.filter(tournament_id=league_id).first()
            if not league:
                league = League.objects.filter(tournament_template_id=league_id).first()
            if not league:
                try:
                    league = League.objects.get(pk=int(league_id))
                except (ValueError, League.DoesNotExist):
                    league = None
            if not league:
                raise Http404("League not found")

        # Sezony (dla danej ligi lub wszystkie)
        seasons = Season.objects.filter(league=league).order_by('-season_id') if league else Season.objects.all().order_by('-season_id')

        # Wybór sezonu z parametru GET (season_id odpowiada polu season_id w modelu)
        season_id = request.GET.get('season_id')
        selected_season = None
        if season_id:
            try:
                season_id_int = int(season_id)
            except (ValueError, TypeError):
                season_id_int = None
            if season_id_int is not None:
                q = Season.objects.filter(season_id=season_id_int)
                if league:
                    q = q.filter(league=league)
                selected_season = q.first()

        if not selected_season:
            selected_season = seasons.first()

        if not selected_season:
            return render(request, 'core/league_table.html', {'table': [], 'seasons': seasons, 'selected_season': None, 'league': league})

        # Pobierz zakończone mecze dla sezonu
        finished_matches = Match.objects.filter(event_stage='3', season=selected_season).select_related('home_team', 'away_team')

        # Obliczanie tabeli
        teams_stats = {}
        for match in finished_matches:
            home_score = match.home_score or 0
            away_score = match.away_score or 0

            for team in (match.home_team, match.away_team):
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

            home_stats = teams_stats[match.home_team.participant_id]
            away_stats = teams_stats[match.away_team.participant_id]

            home_stats['played'] += 1
            home_stats['goals_for'] += home_score
            home_stats['goals_against'] += away_score

            away_stats['played'] += 1
            away_stats['goals_for'] += away_score
            away_stats['goals_against'] += home_score

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

        table = []
        for stats in teams_stats.values():
            stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
            table.append(stats)

        table.sort(key=lambda x: (-x['points'], -x['goal_difference'], -x['goals_for']))

        for idx, team_stats in enumerate(table, 1):
            team_stats['position'] = idx

        return render(request, 'core/league_table.html', {
            'table': table,
            'seasons': seasons,
            'selected_season': selected_season,
            'league': league,
        })
