import requests
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Pobiera WSZYSTKIE drużyny z Premier League (TheSportsDB).'

    def handle(self, *args, **options):
        # 1. Pobieramy model
        try:
            Team = apps.get_model('core', 'Team')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modelu Team."))
            return

        # 2. Ustawiamy API na pobieranie CAŁEJ LIGI
        # Endpoint: search_all_teams.php
        url = "https://www.thesportsdb.com/api/v1/json/3/search_all_teams.php"
        
        # Parametr 'l' to nazwa ligi. TheSportsDB używa: 'English Premier League'
        params = {'l': 'English Premier League'}

        self.stdout.write("⏳ Pobieranie całej ligi z TheSportsDB...")

        try:
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"❌ Błąd sieci: {e}"))
             return

        # 3. Pętla przez wszystkie drużyny
        if data.get('teams'):
            count = 0
            # 'teams' to teraz lista 20 drużyn. Pętla 'for' przejdzie przez każdą z nich.
            for team_data in data['teams']:
                
                obj, created = Team.objects.update_or_create(
                    name=team_data.get('strTeam'),
                    defaults={
                        'logo': team_data.get('strTeamBadge'),
                        'league': team_data.get('strLeague')
                    }
                )
                
                # Wypisujemy w terminalu co się dzieje (opcjonalne, ale fajnie wygląda)
                action = "Dodano" if created else "Zaktualizowano"
                self.stdout.write(f"   -> {action}: {team_data['strTeam']}")
                count += 1
            
            self.stdout.write(self.style.SUCCESS(f"✅ SUKCES! Przetworzono {count} drużyn."))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ API nie zwróciło żadnych drużyn (sprawdź nazwę ligi)."))