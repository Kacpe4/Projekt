import requests
import time
from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware, is_naive

class Command(BaseCommand):
    help = 'Pobiera terminarz 2025-2026 z systemem ponawiania prób (Anti-Ban).'

    def handle(self, *args, **options):
        try:
            Team = apps.get_model('core', 'Team')
            Match = apps.get_model('core', 'Match')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modeli."))
            return

        # USTAWIENIA
        SEASON = '2025-2026'
        LEAGUE_ID = '4328'
        ROUNDS = 38
        
        url = "https://www.thesportsdb.com/api/v1/json/3/eventsround.php"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
        }

        self.stdout.write(f"⏳ Rozpoczynam pobieranie sezonu {SEASON}...")
        total_saved = 0
        new_teams_created = 0

        # Pętla przez wszystkie kolejki
        for r in range(1, ROUNDS + 1):
            self.stdout.write(f"   📥 Sprawdzam kolejkę {r}/{ROUNDS}...")

            # --- MECHANIZM PONAWIANIA PRÓB (RETRY) ---
            attempts = 0
            max_attempts = 3
            success = False
            data = {}

            while attempts < max_attempts and not success:
                try:
                    params = {'id': LEAGUE_ID, 'r': r, 's': SEASON}
                    response = requests.get(url, params=params, headers=headers)
                    
                    # Sprawdź, czy odpowiedź nie jest pusta
                    if not response.text.strip():
                        raise ValueError("Pusta odpowiedź API")

                    data = response.json()
                    success = True  # Udało się, wychodzimy z pętli while

                except Exception as e:
                    attempts += 1
                    wait_time = attempts * 10  # Czekamy 10s, potem 20s, potem 30s
                    self.stdout.write(self.style.WARNING(f"      ⚠️ Błąd sieci (Próba {attempts}/{max_attempts}). Czekam {wait_time}s..."))
                    time.sleep(wait_time)

            if not success:
                self.stdout.write(self.style.ERROR(f"      ❌ Nie udało się pobrać kolejki {r}. Pomijam."))
                continue
            # ---------------------------------------------

            events = data.get('events')
            if not events:
                # To normalne dla odległych terminów
                continue

            for event in events:
                event_id = event.get('idEvent')
                home_name = event.get('strHomeTeam')
                away_name = event.get('strAwayTeam')

                # Tworzenie brakujących drużyn
                home_obj, created_home = Team.objects.get_or_create(
                    name=home_name,
                    defaults={'logo': '', 'league': 'Premier League'}
                )
                if created_home:
                    new_teams_created += 1

                away_obj, created_away = Team.objects.get_or_create(
                    name=away_name,
                    defaults={'logo': '', 'league': 'Premier League'}
                )
                if created_away:
                    new_teams_created += 1

                # Data
                date_str = event.get('strTimestamp')
                dt_obj = parse_datetime(date_str) if date_str else None
                if dt_obj and is_naive(dt_obj):
                    dt_obj = make_aware(dt_obj)

                # Zapis
                Match.objects.update_or_create(
                    id=event_id,
                    defaults={
                        'home_team': home_obj,
                        'away_team': away_obj,
                        'date': dt_obj
                    }
                )
                total_saved += 1
            
            # Standardowa przerwa między kolejkami (2 sekundy)
            time.sleep(2)

        self.stdout.write(self.style.SUCCESS(f"🎉 SUKCES! Pobrano {total_saved} meczów."))
        self.stdout.write(f"   Dodano {new_teams_created} nowych drużyn.")