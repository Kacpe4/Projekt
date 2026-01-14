from django.shortcuts import render, get_object_or_404
from django.views import View
from django.db.models import Q
from .models import Team, Match, Player, MatchStatistic, Season, League
from collections import OrderedDict
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from  .services.prediction_service import MatchPredictionService

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
        # Filtry GET: league_id (tournament_template_id / tournament_id / pk) i season_id (integer)
        league_id = request.GET.get('league_id')
        season_id = request.GET.get('season_id')
        team_id = request.GET.get('team_id')

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

        # lista lig (deduplikacja podobna jak w LeagueTableView)
        leagues_qs = League.objects.all().order_by('name')
        import re
        leagues_map = {}
        for l in leagues_qs:
            if l.tournament_template_id:
                key = f"tpl:{l.tournament_template_id}"
            elif l.tournament_id:
                key = f"tid:{l.tournament_id}"
            else:
                raw_name = (l.name or '').strip().lower()
                raw_name = re.sub(r"\([^)]*\)", "", raw_name)
                raw_name = re.sub(r"\b\d{4}(/\d{2,4}|-\d{2,4})?\b", "", raw_name)
                norm_name = ' '.join(raw_name.split()).strip()
                country = (l.country or '').strip().lower()
                key = f"name:{norm_name}|{country}"
            existing = leagues_map.get(key)
            if existing is None:
                leagues_map[key] = l
            else:
                if (not getattr(existing, 'logo', None)) and getattr(l, 'logo', None):
                    leagues_map[key] = l
        leagues = sorted(leagues_map.values(), key=lambda x: (x.name or '').lower())

        # seasons aggregated for selected league (or all if not selected)
        seasons = _get_seasons_for_league(league)

        # Build matches queryset and apply filters
        matches_qs = Match.objects.all().select_related('home_team', 'away_team', 'season').order_by('-start_time')
        if league:
            # include matches for any League record sharing the same template_id/tournament_id
            if getattr(league, 'tournament_template_id', None):
                matches_qs = matches_qs.filter(season__league__tournament_template_id=league.tournament_template_id)
            elif getattr(league, 'tournament_id', None):
                matches_qs = matches_qs.filter(season__league__tournament_id=league.tournament_id)
            else:
                matches_qs = matches_qs.filter(season__league=league)

        selected_season = None
        if season_id:
            try:
                sid = int(season_id)
            except (ValueError, TypeError):
                sid = None
            if sid is not None:
                # filter by season_id across aggregated leagues
                if league and getattr(league, 'tournament_template_id', None):
                    matches_qs = matches_qs.filter(season__season_id=sid, season__league__tournament_template_id=league.tournament_template_id)
                elif league and getattr(league, 'tournament_id', None):
                    matches_qs = matches_qs.filter(season__season_id=sid, season__league__tournament_id=league.tournament_id)
                elif league:
                    matches_qs = matches_qs.filter(season__season_id=sid, season__league=league)
                else:
                    matches_qs = matches_qs.filter(season__season_id=sid)
                # set selected_season object if exists in seasons list
                for s in seasons:
                    if s.season_id == sid:
                        selected_season = s
                        break

        # selected team
        selected_team = None
        if team_id:
            # Team primary key is participant_id
            selected_team = Team.objects.filter(participant_id=team_id).first() or Team.objects.filter(pk=team_id).first()
            if selected_team:
                matches_qs = matches_qs.filter(Q(home_team=selected_team) | Q(away_team=selected_team))

        # prepare selected_lid for template
        selected_lid = None
        if league:
            selected_lid = league.tournament_template_id or league.tournament_id or str(league.pk)

        # teams list for filter: restrict to seasons if available
        if seasons:
            season_pks = [s.pk for s in seasons]
            teams_qs = Team.objects.filter(Q(home_matches__season__pk__in=season_pks) | Q(away_matches__season__pk__in=season_pks)).distinct().order_by('name')
        else:
            teams_qs = Team.objects.all().order_by('name')

        matches = matches_qs
        return render(request, 'core/matchlist.html', {
            'matches': matches,
            'leagues': leagues,
            'seasons': seasons,
            'teams': teams_qs,
            'selected_lid': selected_lid,
            'selected_season': selected_season,
            'selected_team': selected_team,
        })


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

        # Lista wszystkich lig (do dropdownu)
        # Zwracamy tylko unikalne ligi (deduplikacja po tournament_template_id lub tournament_id)
        leagues_qs = League.objects.all().order_by('name')
        import re
        leagues_map = {}
        for l in leagues_qs:
            # prefer stable identifiers: tournament_template_id, then tournament_id; fallback to normalized name+country
            if l.tournament_template_id:
                key = f"tpl:{l.tournament_template_id}"
            elif l.tournament_id:
                key = f"tid:{l.tournament_id}"
            else:
                # normalize name: strip year ranges like '2024/25', '(2024/25)', '2024-25', single years
                raw_name = (l.name or '').strip().lower()
                raw_name = re.sub(r"\([^)]*\)", "", raw_name)
                raw_name = re.sub(r"\b\d{4}(/\d{2,4}|-\d{2,4})?\b", "", raw_name)
                norm_name = ' '.join(raw_name.split()).strip()
                country = (l.country or '').strip().lower()
                key = f"name:{norm_name}|{country}"
            # choose representative league for this key; prefer one with logo
            existing = leagues_map.get(key)
            if existing is None:
                leagues_map[key] = l
            else:
                # if existing has no logo but this one has, replace
                if (not getattr(existing, 'logo', None)) and getattr(l, 'logo', None):
                    leagues_map[key] = l
        # final list sorted by name
        leagues = sorted(leagues_map.values(), key=lambda x: (x.name or '').lower())

        # stable id for selected league (used by template to mark selected option)
        selected_lid = None
        if league:
            selected_lid = league.tournament_template_id or league.tournament_id or str(league.pk)

        seasons = _get_seasons_for_league(league)

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
                    if league.tournament_template_id:
                        q = q.filter(league__tournament_template_id=league.tournament_template_id)
                    elif league.tournament_id:
                        q = q.filter(league__tournament_id=league.tournament_id)
                    else:
                        q = q.filter(league=league)
                selected_season = q.first()

        if not selected_season:
            selected_season = seasons[0] if seasons else None

        if not selected_season:
            return render(request, 'core/league_table.html', {'table': [], 'seasons': seasons, 'selected_season': None, 'league': league, 'leagues': leagues})

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
            'leagues': leagues,
            'selected_lid': selected_lid,
        })


def _build_table_for_season(selected_season):
    finished_matches = Match.objects.filter(event_stage='3', season=selected_season).select_related('home_team', 'away_team')
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
    return table


class SeasonsByLeagueView(View):
    def get(self, request, league_id):
        # Resolve league (allows tournament_id, tournament_template_id or pk)
        league = League.objects.filter(tournament_id=league_id).first() or League.objects.filter(tournament_template_id=league_id).first()
        if not league:
            try:
                league = League.objects.get(pk=int(league_id))
            except (ValueError, League.DoesNotExist):
                return JsonResponse({'error': 'League not found'}, status=404)
        # Aggregate seasons across all League records that share the same template_id or tournament_id
        seasons = _get_seasons_for_league(league)
        seasons = list(map(lambda s: {'pk': s.pk, 'season_id': s.season_id, 'name': s.name}, seasons))
        return JsonResponse({'seasons': seasons})


class LeagueTablePartialView(View):
    def get(self, request, league_id):
        # reuse logic to resolve league + season
        league = League.objects.filter(tournament_id=league_id).first()
        if not league:
            league = League.objects.filter(tournament_template_id=league_id).first()
        if not league:
            try:
                league = League.objects.get(pk=int(league_id))
            except (ValueError, League.DoesNotExist):
                return JsonResponse({'error': 'League not found'}, status=404)
        seasons = _get_seasons_for_league(league)
        season_id = request.GET.get('season_id')
        selected_season = None
        if season_id:
            try:
                season_id_int = int(season_id)
            except (ValueError, TypeError):
                season_id_int = None
            if season_id_int is not None:
                if league.tournament_template_id:
                    selected_season = Season.objects.filter(league__tournament_template_id=league.tournament_template_id, season_id=season_id_int).first()
                elif league.tournament_id:
                    selected_season = Season.objects.filter(league__tournament_id=league.tournament_id, season_id=season_id_int).first()
                else:
                    selected_season = Season.objects.filter(league=league, season_id=season_id_int).first()
        if not selected_season:
            selected_season = seasons[0] if seasons else None
        if not selected_season:
            html = render_to_string('core/_league_table_partial.html', {'table': [], 'selected_season': None, 'seasons': seasons, 'league': league})
            return JsonResponse({'html': html})
        table = _build_table_for_season(selected_season)
        html = render_to_string('core/_league_table_partial.html', {'table': table, 'selected_season': selected_season, 'seasons': seasons, 'league': league})
        return JsonResponse({'html': html})


def _get_seasons_for_league(league):
    """Zwraca listę obiektów Season dla danej ligi, agregując rekordy powiązane przez tournament_template_id lub tournament_id.
    Deduplicuje po season_id, zachowując porządek malejący season_id.
    Jeśli league jest None -> zwraca wszystkie sezony.
    """
    if not league:
        qs = Season.objects.all().order_by('-season_id')
    else:
        if getattr(league, 'tournament_template_id', None):
            qs = Season.objects.filter(league__tournament_template_id=league.tournament_template_id).order_by('-season_id')
        elif getattr(league, 'tournament_id', None):
            qs = Season.objects.filter(league__tournament_id=league.tournament_id).order_by('-season_id')
        else:
            qs = Season.objects.filter(league=league).order_by('-season_id')
    seen = set()
    seasons = []
    for s in qs:
        sid = s.season_id
        if sid in seen:
            continue
        seen.add(sid)
        seasons.append(s)
    return seasons


class MatchPredictionView(View):
    """Widok do przewidywania wyników meczów"""

    def get(self, request):
        """Wyświetla stronę z przewidywaniami nadchodzących meczów"""
        service = MatchPredictionService()

        # Trenuj model jeśli nie jest wytrenowany
        if not service.is_trained:
            success, message = service.train_model()
            if not success:
                return render(request, 'core/match_prediction.html', {
                    'error': message,
                    'predictions': []
                })

        # Pobierz przewidywania dla nadchodzących meczów
        predictions = service.get_upcoming_matches_predictions(limit=20)

        return render(request, 'core/match_prediction.html', {
            'predictions': predictions,
            'error': None
        })


class PredictSpecificMatchView(View):
    """Widok do przewidywania konkretnego meczu"""

    def get(self, request, match_id):
        """Przewiduje wynik konkretnego meczu"""
        match = get_object_or_404(Match, event_id=match_id)

        service = MatchPredictionService()
        prediction = service.predict_match(match.home_team, match.away_team)

        return render(request, 'core/match_prediction_detail.html', {
            'match': match,
            'prediction': prediction
        })


class PredictCustomMatchView(View):
    """Widok do przewidywania dowolnego meczu między dwiema drużynami"""

    def get(self, request):
        """Wyświetla formularz wyboru drużyn"""
        teams = Team.objects.all().order_by('name')

        home_team_id = request.GET.get('home_team')
        away_team_id = request.GET.get('away_team')

        prediction = None
        home_team = None
        away_team = None

        if home_team_id and away_team_id:
            try:
                home_team = Team.objects.get(participant_id=home_team_id)
                away_team = Team.objects.get(participant_id=away_team_id)

                service = MatchPredictionService()
                prediction = service.predict_match(home_team, away_team)
            except Team.DoesNotExist:
                prediction = {'error': 'Nie znaleziono wybranej drużyny'}

        return render(request, 'core/match_prediction_custom.html', {
            'teams': teams,
            'home_team': home_team,
            'away_team': away_team,
            'prediction': prediction
        })
