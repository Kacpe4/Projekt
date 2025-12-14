import requests
from datetime import datetime
from typing import List, Dict, Optional
from django.db import transaction
from django.conf import settings
import os
from pathlib import Path
from dotenv import load_dotenv

from ..models import (
    League, Season, Team, Match, MatchStatistic, StatDefinition,
    Player, Country, TeamSquad
)

# Załaduj .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')


class FootballDataService:
    BASE_URL = "https://api.sportdb.dev/api/flashscore"

    def __init__(self):
        self.session = requests.Session()

        # Pobierz API key
        self.api_key = os.getenv('SPORTDB_API_KEY') or getattr(settings, 'SPORTDB_API_KEY', None)

        if not self.api_key:
            raise ValueError(
                "❌ SPORTDB_API_KEY not found!\n"
                f"Create . env file at:  {BASE_DIR / '.env'}\n"
                "With:  SPORTDB_API_KEY=your_api_key_here"
            )

        # Ustaw autoryzację
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
        })

        print(f"✓ API initialized with key: {self.api_key[: 10]}...")

    # ============ METODY DLA MECZY ============

    def fetch_matches(self, country_id: str, league_template_id: str,
                      season: str, page: int = 1) -> List[Dict]:
        """Pobiera listę meczy dla danej ligi i sezonu"""
        url = f"{self.BASE_URL}/football/{country_id}/{league_template_id}/{season}/results"
        params = {'page': page}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            return data.get('results', []) if isinstance(data, dict) else data

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error {response.status_code}: {e}")
            print(f"   URL: {url}")
            print(f"   Response: {response.text[: 500]}")
            raise

    def fetch_match_stats(self, event_id: str) -> List[Dict]:
        """Pobiera statystyki dla konkretnego meczu"""
        url = f"{self.BASE_URL}/match/{event_id}/stats"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            print(f"❌ Error fetching stats for {event_id}: {e}")
            raise

    @transaction.atomic
    def save_match(self, match_data: Dict) -> Match:
        """Zapisuje mecz do bazy danych"""

        # ✅ LIGA
        league, _ = League.objects.get_or_create(
            tournament_id=match_data['tournamentId'],
            defaults={
                'tournament_template_id': match_data['tournamentTemplateId'],
                'name': match_data['tournamentName'],
                'country': match_data['tournamentName'].split(':  ')[0].strip()
            }
        )

        # ✅ SEZON
        season, _ = Season.objects.get_or_create(
            league=league,
            season_id=match_data['season'],
            defaults={
                'name': match_data.get('seasonName', 'Unknown'),
                'tournament_stage_id': match_data['tournamentStageId']
            }
        )

        # ✅ DRUŻYNA GOSPODARZY
        home_team, _ = Team.objects.get_or_create(
            participant_id=match_data['homeParticipantIds'],
            defaults={
                'name': match_data['homeName'],
                'short_name': match_data['homeFirstName'],
                'three_char_name': match_data['home3CharName'],
                'logo': f"https://static.flashscore.com/res/image/data/{match_data['homeLogo']}",
                'slug': match_data['homeParticipantNameUrl'],
            }
        )

        # ✅ DRUŻYNA GOŚCI
        away_team, _ = Team.objects.get_or_create(
            participant_id=match_data['awayParticipantIds'],
            defaults={
                'name': match_data['awayName'],
                'short_name': match_data['awayFirstName'],
                'three_char_name': match_data['away3CharName'],
                'logo': f"https://static.flashscore.com/res/image/data/{match_data['awayLogo']}",
                'slug': match_data['awayParticipantNameUrl'],
            }
        )

        # ✅ KONWERSJA DATY
        start_time = datetime.fromisoformat(
            match_data['startDateTimeUtc'].replace('Z', '+00:00')
        )

        # ✅ MAPOWANIE eventStage na event_stage_id
        event_stage_mapping = {
            'SCHEDULED': '1',
            'LIVE': '2',
            'FINISHED': '3',
            'POSTPONED': '4',
            'CANCELLED': '5',
        }

        event_stage_raw = match_data.get('eventStage', '')
        event_stage = event_stage_mapping.get(event_stage_raw, match_data.get('eventStageId', '1'))

        # ✅ UTWÓRZ LUB ZAKTUALIZUJ MECZ
        match, created = Match.objects.update_or_create(
            event_id=match_data['eventId'],
            defaults={
                'season': season,
                'round': match_data['round'],
                'home_team': home_team,
                'away_team': away_team,
                'home_event_participant_id': match_data['homeEventParticipantId'],
                'away_event_participant_id': match_data['awayEventParticipantId'],
                'start_time': start_time,
                'start_utime': int(match_data['startUtime']),
                'event_stage': event_stage,  # ✅ Teraz poprawnie '3' dla FINISHED
                'event_stage_id': match_data.get('eventStageId', event_stage),
                'home_score': int(match_data.get('homeScore', 0) or 0),
                'away_score': int(match_data.get('awayScore', 0) or 0),
                'home_full_time_score': int(match_data.get('homeFullTimeScore', 0) or 0),
                'away_full_time_score': int(match_data.get('awayFullTimeScore', 0) or 0),
                'home_halftime_score': int(match_data.get('homeResultPeriod2', 0) or 0),
                'away_halftime_score': int(match_data.get('awayResultPeriod2', 0) or 0),
                'winner': match_data.get('winner'),
                'ft_winner': match_data.get('ftWinner'),
                'has_live_centre': bool(int(match_data.get('hasLiveCentre', 0))),
                'has_lineups': bool(int(match_data.get('lineps', 0))),
                'home_goal_under_review': int(match_data.get('homeGoalUnderReview', 0)),
                'away_goal_under_review': int(match_data.get('awayGoalUnderReview', 0)),
            }
        )

        return match

    @transaction.atomic
    def save_match_statistics(self, event_id: str, stats_data: List[Dict]):
        """Zapisuje statystyki meczu do bazy danych"""
        try:
            match = Match.objects.get(event_id=event_id)
        except Match.DoesNotExist:
            raise ValueError(f"Match with event_id {event_id} does not exist")

        # Usuń stare statystyki (opcjonalnie - jeśli chcesz aktualizować)
        # match.statistics.all().delete()

        period_mapping = {
            'Match': 'match',
            '1st Half': '1st_half',
            '2nd Half': '2nd_half'
        }

        for period_data in stats_data:
            period = period_mapping.get(period_data['period'], 'match')

            for stat in period_data['stats']:
                # Zapisz definicję statystyki
                StatDefinition.objects.get_or_create(
                    stat_id=stat['statId'],
                    defaults={'stat_name': stat['statName']}
                )

                # ✅ ZMIANA: użyj update_or_create zamiast create
                MatchStatistic.objects.update_or_create(
                    match=match,
                    period=period,
                    stat_id=stat['statId'],
                    stat_name=stat['statName'],
                    defaults={
                        'home_value': stat['homeValue'],
                        'away_value': stat['awayValue']
                    }
                )

    def fetch_and_save_season(self, country_id: str, league_template_id: str,
                              season: str, max_pages: int = 10):
        """
        Pobiera i zapisuje wszystkie mecze z danego sezonu
        """
        all_matches = []

        for page in range(1, max_pages + 1):
            print(f"📄 Fetching page {page}...")

            try:
                matches = self.fetch_matches(country_id, league_template_id, season, page)
            except Exception as e:
                print(f"❌ Error fetching page {page}: {e}")
                break

            if not matches:
                print(f"✓ No more matches on page {page}")
                break

            print(f"   Found {len(matches)} matches")

            for match_data in matches:
                try:
                    match = self.save_match(match_data)
                    all_matches.append(match)

                    # Pobierz statystyki tylko dla zakończonych meczy
                    if match.event_stage == '3':  # FINISHED
                        try:
                            print(f"   📊 Fetching stats for {match.event_id}...")
                            stats = self.fetch_match_stats(match.event_id)
                            self.save_match_statistics(match.event_id, stats)
                        except Exception as e:
                            print(f"   ⚠️  Error fetching stats:  {e}")

                except Exception as e:
                    print(f"❌ Error saving match:  {e}")
                    continue

            # Jeśli mniej niż 20 meczy, prawdopodobnie ostatnia strona
            if len(matches) < 20:
                print(f"✓ Reached last page (page {page})")
                break

        print(f"\n✅ Total matches saved: {len(all_matches)}")
        return all_matches

    # ============ METODY DLA DRUŻYN I ZAWODNIKÓW ============

    def fetch_team_details(self, team_slug: str, team_id: str) -> Dict:
        """Pobiera szczegóły drużyny wraz z kadrą"""
        url = f"{self.BASE_URL}/team/{team_slug}/{team_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error fetching team {team_slug}:  {e}")
            raise

    @transaction.atomic
    def save_team_details(self, team_data: Dict) -> Team:
        """Zapisuje szczegóły drużyny do bazy danych"""
        team = Team.objects.get(participant_id=team_data['id'])

        # Aktualizuj szczegóły drużyny
        team.slug = team_data.get('slug', team.slug)
        team.name = team_data.get('teamName', team.name)
        team.logo = team_data.get('teamLogo', '')
        team.team_class = team_data.get('teamClass', '')
        team.stadium_name = team_data.get('stadiumName', '')
        team.stadium_capacity = team_data.get('stadiumCapacity')
        team.details_fetched = True
        team.save()

        return team

    @transaction.atomic
    def save_team_squad(self, team: Team, squad_data: List[Dict]):
        """Zapisuje kadrę drużyny do bazy danych"""
        for tournament_squad in squad_data:
            tournament_id = tournament_squad.get('tournamentId', '')
            tournament_type = tournament_squad.get('tournamentType', '')

            for player_data in tournament_squad.get('players', []):
                # Zapisz kraj
                country = None
                if player_data.get('countryId'):
                    country, _ = Country.objects.get_or_create(
                        country_id=player_data['countryId'],
                        defaults={'name': player_data.get('countryName', 'Unknown')}
                    )

                # Zapisz zawodnika
                player, created = Player.objects.update_or_create(
                    player_id=player_data['id'],
                    defaults={
                        'slug': player_data['slug'],
                        'first_name': player_data.get('firstName', ''),
                        'last_name': player_data.get('lastName', 'Unknown'),
                        'position': player_data.get('position', 'Unknown'),
                        'country': country,
                    }
                )

                # Dodaj do składu
                TeamSquad.objects.update_or_create(
                    team=team,
                    player=player,
                    tournament_id=tournament_id,
                    defaults={
                        'tournament_type': tournament_type,
                        'jersey_number': player_data.get('jerseyNumber', ''),
                    }
                )

                if created:
                    print(f"  ✓ Created player:  {player.full_name}")

    def fetch_and_save_team_with_squad(self, team_slug: str, team_id: str):
        """Pobiera i zapisuje drużynę wraz z pełną kadrą"""
        print(f"🔍 Fetching team details for {team_slug}...")

        # Pobierz dane z API
        team_data = self.fetch_team_details(team_slug, team_id)

        # Zapisz szczegóły drużyny
        team = self.save_team_details(team_data)
        print(f"✓ Saved team:  {team.name}")

        # Zapisz kadrę
        if 'squad' in team_data:
            print(f"  Saving squad...")
            self.save_team_squad(team, team_data['squad'])

            # Policz zawodników
            total_players = Player.objects.filter(teams__team=team).distinct().count()
            print(f"✓ Team {team.name} now has {total_players} players")

        return team

    def fetch_matches(self, country_id: str, league_template_id: str,
                      season: str, page: int = 1) -> List[Dict]:
        """Pobiera listę meczy dla danej ligi i sezonu"""

        # Usuń spacje jeśli są
        country_id = country_id.replace(' ', '')
        league_template_id = league_template_id.replace(' ', '')

        url = f"{self.BASE_URL}/football/{country_id}/{league_template_id}/{season}/results"
        params = {'page': page}

        print(f"📡 Full URL: {url}? page={page}")

        try:
            response = self.session.get(url, params=params)
            print(f"   Status Code: {response.status_code}")

            response.raise_for_status()

            # Pokaż surową odpowiedź
            raw_text = response.text
            print(f"   Raw response (first 500 chars): {raw_text[:500]}")

            data = response.json()
            print(f"   Data type: {type(data)}")

            if isinstance(data, dict):
                print(f"   Keys: {list(data.keys())}")

                # Spróbuj różnych kluczy
                for key in ['results', 'data', 'matches', 'events', 'items']:
                    if key in data:
                        print(f"   Found data under key: '{key}' with {len(data[key])} items")
                        return data[key]

                # Jeśli żaden klucz nie pasuje, zwróć całą odpowiedź
                print(f"   ⚠️ Unknown structure, returning full response")
                return [data] if data else []

            elif isinstance(data, list):
                print(f"   Direct list with {len(data)} items")
                return data
            else:
                print(f"   ⚠️ Unexpected data type: {type(data)}")
                return []

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"   Response text: {response.text[: 1000]}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise
    def fetch_all_teams_squads(self, only_without_details: bool = True):
        """Pobiera kadry dla wszystkich drużyn w bazie"""
        teams = Team.objects.all()

        if only_without_details:
            teams = teams.filter(details_fetched=False)

        print(f"Found {teams.count()} teams to fetch squads for...")

        for team in teams:
            try:
                self.fetch_and_save_team_with_squad(team.slug, team.participant_id)
            except Exception as e:
                print(f"✗ Error fetching squad for {team.name}: {e}")
                continue