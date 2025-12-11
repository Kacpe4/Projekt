import requests
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = 'Pobiera piłkarzy z TheSportsDB (Darmowy klucz).'

    def handle(self, *args, **options):
        # 1. Pobieramy modele
        try:
            Team = apps.get_model('core', 'Team')
            Player = apps.get_model('core', 'Player')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modeli."))
            return

        # 2. Szukamy drużyny w bazie
        try:
            man_utd = Team.objects.get(name='Manchester United')
        except Team.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ Najpierw uruchom fetch_team!"))
            return

        # Oficjalny endpoint TheSportsDB do szukania piłkarzy
        url = "https://www.thesportsdb.com/api/v1/json/3/searchplayers.php"
        params = {'t': 'Manchester United'}

        self.stdout.write("⏳ Pobieranie piłkarzy z TheSportsDB...")

        try:
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Błąd sieci: {e}"))
            return

        # Klucz w JSON to 'player'
        if data.get('player'):
            count = 0
            for item in data['player']:
                # Pobieramy pozycję (czasem jest pusta)
                pos = item['strPosition']
                if not pos:
                    pos = "Nieznana"

                Player.objects.update_or_create(
                    name=item['strPlayer'],
                    team=man_utd,
                    defaults={
                        'position': pos
                    }
                )
                count += 1
            
            self.stdout.write(self.style.SUCCESS(f"✅ Sukces! Zapisano {count} piłkarzy."))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ API nie zwróciło piłkarzy (może darmowy klucz ma limity dla tej drużyny)."))