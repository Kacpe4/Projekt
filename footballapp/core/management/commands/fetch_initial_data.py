import requests
import time
from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive

class Command(BaseCommand):
    help = 'Pobiera komplet danych (Liga -> Sezon -> Drużyny -> Mecze).'

    def handle(self, *args, **options):
        # 1. Modele
        try:
            League = apps.get_model('core', 'League')
            Season = apps.get_model('core', 'Season')
            Team = apps.get_model('core', 'Team')
            Match = apps.get_model('core', 'Match')
            Country = apps.get_model('core', 'Country')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modeli."))
            return

        API_LEAGUE_ID = '4328'
        SEASON_NAME = '2025-2026'
        HEADERS = {"User-Agent": "Mozilla/5.0"}

        self.stdout.write("🚀 Inicjalizacja...")

        # Tworzenie Anglii
        england, _ = Country.objects.get_or_create(country_id=1, defaults={'name': 'England'})
        
        # Tworzenie Ligi
        premier_league, _ = League.objects.get_or_create(
            tournament_id=API_LEAGUE_ID,
            defaults={'name': 'Premier League', 'country': 'England', 'tournament_template_id': API_LEAGUE_ID}
        )
        
        # Tworzenie Sezonu
        current_season, _ = Season.objects.get_or_create(
            league=premier_league, season_id=2025, 
            defaults={'name': SEASON_NAME, 'tournament_stage_id': 'Regular Season'}
        )

        # Pobieranie Drużyn
        self.stdout.write("⏳ Pobieranie drużyn...")
        teams_url = "https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php"
        try:
            r = requests.get(teams_url, params={'l': 'English Premier League'}, headers=HEADERS)
            data = r.json()
            if data.get('teams'):
                count = 0
                for item in data['teams']:
                    Team.objects.update_or_create(
                        participant_id=item['idTeam'],
                        defaults={
                            'name': item['strTeam'],
                            'logo': item.get('strTeamBadge', ''),
                            'slug': item['strTeam'].lower().replace(' ', '-')
                        }
                    )
                    count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Pobrano {count} drużyn."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Błąd drużyn: {e}"))

        # Pobieranie Meczów (Terminarz)
        self.stdout.write("⏳ Pobieranie terminarza...")
        rounds_url = "https://www.thesportsdb.com/api/v1/json/3/eventsround.php"
        total_matches = 0
        
        for r in range(1, 39):
            try:
                resp = requests.get(rounds_url, params={'id': API_LEAGUE_ID, 'r': r, 's': SEASON_NAME}, headers=HEADERS)
                events = resp.json().get('events')
                if not events: continue

                for event in events:
                    home_id = event.get('idHomeTeam')
                    away_id = event.get('idAwayTeam')
                    
                    try:
                        home_obj = Team.objects.get(participant_id=home_id)
                        away_obj = Team.objects.get(participant_id=away_id)
                    except Team.DoesNotExist:
                        continue # Pomijamy jeśli brak drużyny

                    date_str = event.get('strTimestamp')
                    dt_obj = parse_datetime(date_str) if date_str else None
                    if dt_obj and is_naive(dt_obj): dt_obj = make_aware(dt_obj)
                    if not dt_obj: continue

                    Match.objects.update_or_create(
                        event_id=event['idEvent'],
                        defaults={
                            'season': current_season,
                            'round': f"Round {r}",
                            'home_team': home_obj,
                            'away_team': away_obj,
                            'home_event_participant_id': home_id,
                            'away_event_participant_id': away_id,
                            'start_time': dt_obj,
                            'start_utime': 0,
                            'event_stage': '1',
                            'event_stage_id': '1'
                        }
                    )
                    total_matches += 1
                time.sleep(0.5)
            except Exception:
                continue

        self.stdout.write(self.style.SUCCESS(f"🎉 Baza gotowa! Mecze: {total_matches}."))