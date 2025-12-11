import requests
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Pobiera piłkarzy Manchesteru United (Sezon 2023) i zapisuje do bazy.'

    def handle(self, *args, **options):
        # 1. Pobieramy modele
        try:
            Team = apps.get_model('core', 'Team')
            Player = apps.get_model('core', 'Player')
        except LookupError:
            self.stdout.write(self.style.ERROR("Błąd: Nie znaleziono modeli."))
            return

        # 2. Musimy mieć drużynę w bazie, żeby przypisać do niej piłkarza
        try:
            man_utd = Team.objects.get(name='Manchester United')
        except Team.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ BŁĄD: Najpierw pobierz drużynę (fetch_team)!"))
            return

        # 3. Konfiguracja API
        API_KEY = os.getenv('API_KEY')
        headers = {'x-rapidapi-key': API_KEY}
        
        # Dokumentacja mówi: endpoint /players wymaga ID drużyny i sezonu
        params = {
            'team': 33,      # ID Manchesteru United w tym API
            'season': 2023   # Pobieramy obecny/ostatni pełny skład
        }

        self.stdout.write("⏳ Pobieranie piłkarzy...")

        try:
            # TO JEST KLUCZOWE: Łączymy się z API
            response = requests.get('https://v3.football.api-sports.io/players', headers=headers, params=params)
            data = response.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Błąd sieci: {e}"))
            return

        # 4. Pętla: Wyciągamy dane z JSON-a i zapisujemy do SQL
        if data.get('response'):
            count = 0
            for item in data['response']:
                player_info = item['player']
                statistics = item['statistics'][0] # Statystyki (pozycja itp.)
                
                # Zapisujemy do bazy (update_or_create zapobiega duplikatom)
                Player.objects.update_or_create(
                    name=player_info['name'],
                    team=man_utd,  # Przypisujemy piłkarza do drużyny (Relacja!)
                    defaults={
                        'position': statistics['games']['position'] or "Nieznana"
                    }
                )
                count += 1
            
            self.stdout.write(self.style.SUCCESS(f"✅ Sukces! Zapisano {count} piłkarzy."))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ API nie zwróciło danych: {data.get('errors', 'Brak wyników')}"))