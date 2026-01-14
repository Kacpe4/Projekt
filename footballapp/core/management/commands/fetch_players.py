import requests
import time
from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Pobiera piłkarzy używając PEŁNEJ listy aliasów.'

    def handle(self, *args, **options):
        try:
            Team = apps.get_model('core', 'Team')
            Player = apps.get_model('core', 'Player')
            TeamSquad = apps.get_model('core', 'TeamSquad')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modeli."))
            return

        all_teams = Team.objects.all()
        self.stdout.write(f"Znaleziono {all_teams.count()} drużyn. Start...")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
        }
        url = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"

        # --- WIELKA LISTA TŁUMACZEŃ (Twoja Baza -> API) ---
        # Dzięki temu API zawsze zrozumie o kogo pytamy
        SEARCH_ALIASES = {
            # Nazwa w Twojej Bazie       : Nazwa dla API
            "Wolverhampton Wanderers": "Wolves",
            "Brighton and Hove Albion": "Brighton",
            "Nottingham Forest": "Nottingham",
            "Tottenham Hotspur": "Tottenham",
            "West Ham United": "West Ham",
            "Newcastle United": "Newcastle",
            "Sheffield United": "Sheffield",
            "Luton Town": "Luton",
            "Manchester United": "Man United",
            "Manchester City": "Man City",
            "AFC Bournemouth": "Bournemouth",
            "Leeds United": "Leeds",
            "Leicester City": "Leicester",
            "Norwich City": "Norwich",
            "Watford": "Watford",
            "Brentford": "Brentford",
            "Crystal Palace": "Crystal Palace",
            "Aston Villa": "Aston Villa" 
            # Arsenal, Chelsea, Liverpool, Everton, Fulham, Burnley zazwyczaj działają bez zmian
        }

        total_saved_global = 0

        for i, team in enumerate(all_teams, 1):
            # Tu sprawdzamy, czy mamy tłumaczenie. Jeśli nie, bierzemy oryginalną nazwę.
            search_name = SEARCH_ALIASES.get(team.name, team.name)
            
            self.stdout.write(f"[{i}/{all_teams.count()}] ⏳ Szukam: '{search_name}' (Baza: {team.name})...", ending='')

            try:
                response = requests.get(url, params={'t': search_name}, headers=headers)
                data = response.json() if response.status_code == 200 else {}
            except Exception:
                self.stdout.write(self.style.ERROR(" ❌ Błąd sieci"))
                continue

            if not data.get('player'):
                self.stdout.write(self.style.WARNING(f" ⚠️ Pusto"))
                continue

            saved_count = 0
            
            for item in data['player']:
                try:
                    # Logika pobierania (identyczna jak wcześniej)
                    api_player_id = item.get('idPlayer')
                    full_name = item.get('strPlayer', 'Unknown')
                    
                    raw_pos = item.get('strPosition')
                    pos = 'Midfielders'
                    if raw_pos == "Goalkeeper": pos = 'Goalkeepers'
                    elif raw_pos == "Defender": pos = 'Defenders'
                    elif raw_pos == "Midfielder": pos = 'Midfielders'
                    elif raw_pos == "Forward": pos = 'Forwards'

                    parts = full_name.split(' ', 1)
                    f_name = parts[0]
                    l_name = parts[1] if len(parts) > 1 else ""

                    player_obj, _ = Player.objects.update_or_create(
                        player_id=api_player_id,
                        defaults={
                            'first_name': f_name, 'last_name': l_name,
                            'slug': slugify(f"{f_name}-{l_name}-{api_player_id}"),
                            'position': pos
                        }
                    )

                    TeamSquad.objects.update_or_create(
                        team=team, player=player_obj,
                        defaults={'jersey_number': item.get('strNumber') or "", 'tournament_id': '4328'}
                    )
                    saved_count += 1
                    total_saved_global += 1

                except Exception:
                    continue

            if saved_count > 0:
                self.stdout.write(self.style.SUCCESS(f" ✅ Dodano {saved_count}"))
            else:
                self.stdout.write(self.style.WARNING(" ⚠️ Pusto (mimo poprawnej odpowiedzi)"))

            # Zwiększyłem czas, żeby API nie blokowało innych klubów po pobraniu Arsenalu
            time.sleep(1.2) 

        self.stdout.write(self.style.SUCCESS(f"🎉 KONIEC! Mamy {total_saved_global} piłkarzy w bazie."))