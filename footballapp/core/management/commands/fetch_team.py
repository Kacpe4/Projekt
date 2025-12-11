import requests
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Pobiera dane drużyny z TheSportsDB (Darmowy klucz).'

    def handle(self, *args, **options):
        # 1. Pobieramy model
        try:
            Team = apps.get_model('core', 'Team')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modelu Team."))
            return

        # Używamy oficjalnego, darmowego API TheSportsDB
        url = "https://www.thesportsdb.com/api/v1/json/3/searchteams.php"
        params = {'t': 'Manchester United'}

        self.stdout.write("⏳ Pobieranie drużyny z TheSportsDB...")

        try:
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"❌ Błąd sieci: {e}"))
             return

        # Sprawdzenie czy są dane
        if data.get('teams'):
            team_data = data['teams'][0] # Pierwszy wynik
            
            # --- TU BYŁ BŁĄD, TERAZ JEST POPRAWIONE ---
            # Zmieniłem "team, _ =" na "obj, created ="
            obj, created = Team.objects.update_or_create(
                name=team_data.get('strTeam'),
                defaults={
                    'logo': team_data.get('strTeamBadge'),
                    'league': team_data.get('strLeague')
                }
            )
            # ------------------------------------------
            
            action = "Dodano" if created else "Zaktualizowano"
            self.stdout.write(self.style.SUCCESS(f"✅ {action}: {team_data['strTeam']}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ API nie znalazło drużyny."))