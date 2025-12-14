from django.core.management.base import BaseCommand
from core.services.footballdata_service import FootballDataService


class Command(BaseCommand):
    help = 'Fetch football match data from API'

    def add_arguments(self, parser):
        # Usuń spacje z wartości domyślnych
        parser.add_argument('--country-id', type=str, default='england: 198')  # BEZ SPACJI!
        parser.add_argument('--league-id', type=str, default='premier-league: dYlOSQOD')  # BEZ SPACJI!
        parser.add_argument('--season', type=str, default='2024-2025')  # Może sezon 2025-2026 jeszcze nie istnieje?
        parser.add_argument('--max-pages', type=int, default=10)
        parser.add_argument('--fetch-squads', action='store_true', help='Fetch team squads too')

    def handle(self, *args, **options):
        service = FootballDataService()

        country_id = options['country_id']
        league_id = options['league_id']
        season = options['season']
        max_pages = options['max_pages']

        self.stdout.write(f'Fetching data for {league_id} - {season}...')
        self.stdout.write(f'URL will be: {service.BASE_URL}/football/{country_id}/{league_id}/{season}/results')

        matches = service.fetch_and_save_season(
            country_id=country_id,
            league_template_id=league_id,
            season=season,
            max_pages=max_pages
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully fetched {len(matches)} matches')
        )

        if options['fetch_squads']:
            self.stdout.write('Fetching team squads...')
            service.fetch_all_teams_squads(only_without_details=True)
            self.stdout.write(self. style.SUCCESS('Squads fetched! '))