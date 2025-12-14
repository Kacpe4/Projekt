import requests
import time
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Pobiera piłkarzy z systemem ponawiania prób (Anti-Ban).'

    def handle(self, *args, **options):
        # 1. Modele
        try:
            Team = apps.get_model('core', 'Team')
            Player = apps.get_model('core', 'Player')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modeli."))
            return

        all_teams = Team.objects.all()
        if not all_teams.exists():
            self.stdout.write(self.style.ERROR("❌ Baza drużyn jest pusta!"))
            return

        self.stdout.write(f"Znaleziono {all_teams.count()} drużyn. Rozpoczynam pobieranie...")

        # URL-e
        search_team_url = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php"
        lookup_players_url = "https://www.thesportsdb.com/api/v1/json/3/lookup_all_players.php"

        # Udajemy przeglądarkę (żeby API nas łagodniej traktowało)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        for i, team in enumerate(all_teams, 1):
            self.stdout.write(f"[{i}/{all_teams.count()}] ⏳ Pobieranie dla: {team.name}...")

            # --- MECHANIZM PONAWIANIA PRÓB (RETRY) ---
            attempts = 0
            max_attempts = 3
            success = False

            while attempts < max_attempts and not success:
                try:
                    # KROK 1: Pobierz ID
                    r_team = requests.get(search_team_url, params={'t': team.name}, headers=headers)
                    d_team = r_team.json()

                    if not d_team.get('teams'):
                        self.stdout.write(self.style.WARNING(f"   ⚠️ Nie znaleziono ID dla {team.name}"))
                        break # Przerywamy pętlę while, idziemy do nast. drużyny

                    team_api_id = d_team['teams'][0]['idTeam']

                    # KROK 2: Pobierz Piłkarzy
                    r_players = requests.get(lookup_players_url, params={'id': team_api_id}, headers=headers)
                    d_players = r_players.json()

                    if d_players.get('player'):
                        count = 0
                        for item in d_players['player']:
                            pos = item.get('strPosition')
                            if not pos: pos = "Nieznana"

                            Player.objects.update_or_create(
                                name=item['strPlayer'],
                                team=team,
                                defaults={'position': pos}
                            )
                            count += 1
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Sukces! Zapisano {count} piłkarzy."))
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠️ API zwróciło pustą listę piłkarzy."))

                    success = True # Udało się, wychodzimy z pętli while

                except Exception as e:
                    attempts += 1
                    wait_time = attempts * 5 # Czekamy 5s, potem 10s, potem 15s
                    self.stdout.write(self.style.WARNING(f"   ⚠️ Błąd sieci (Próba {attempts}/{max_attempts}). Czekam {wait_time}s..."))
                    time.sleep(wait_time)
            
            if not success:
                self.stdout.write(self.style.ERROR(f"   ❌ Nie udało się pobrać danych dla {team.name} po {max_attempts} próbach."))

            # Standardowa przerwa między drużynami (4 sekundy dla bezpieczeństwa)
            time.sleep(4)

        self.stdout.write(self.style.SUCCESS("🎉 Zakończono pobieranie całej ligi!"))