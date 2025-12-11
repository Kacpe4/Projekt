from django.core.management.base import BaseCommand
from django.apps import apps
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class Command(BaseCommand):
    help = 'Pobiera dane drużyny.'

    def handle(self, *args, **options):
        # --- INTELIGENTNE POBIERANIE MODELU ---
        Team = None
        try:
            Team = apps.get_model('core', 'Team') # Próba 1: krótka nazwa
        except LookupError:
            try:
                Team = apps.get_model('footballapp.core', 'Team') # Próba 2: długa nazwa
            except LookupError:
                # Jeśli obie zawiodą, wypisz co widzi Django
                self.stdout.write(self.style.ERROR("❌ BŁĄD KRYTYCZNY: Django nie widzi Twojej aplikacji."))
                self.stdout.write("Dostępne aplikacje w systemie to:")
                for app in apps.get_app_configs():
                    self.stdout.write(f" - {app.label} (nazwa: {app.name})")
                return
        # --------------------------------------

        API_KEY = os.getenv('API_KEY')
        if not API_KEY:
            self.stdout.write(self.style.ERROR("Brak klucza API w .env"))
            return

        headers = {'x-rapidapi-key': API_KEY}
        params = {'league': 39, 'season': 2021, 'id': 33}

        self.stdout.write("Pobieranie danych...")
        try:
            response = requests.get('https://v3.football.api-sports.io/teams', headers=headers, params=params)
            data = response.json()
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"Błąd sieci: {e}"))
             return

        if data.get('response'):
            team_data = data['response'][0]['team']
            Team.objects.update_or_create(
                name=team_data['name'],
                defaults={'logo': team_data['logo'], 'league': 'Premier League'}
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Sukces! Zapisano: {team_data['name']}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️ API odpowiedziało, ale brak danych."))