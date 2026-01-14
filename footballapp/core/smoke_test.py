from django.test import Client
from core.models import League, Season, Team, Match
from django.utils import timezone

# Create sample league and season
league, created = League.objects.get_or_create(
    tournament_id='TEST_LEAGUE',
    defaults={
        'tournament_template_id': 'TEMPLATE_TEST',
        'name': 'Test League',
        'country': 'Testland',
        'logo': '',
    }
)
season, _ = Season.objects.get_or_create(
    league=league,
    season_id=2026,
    defaults={'name': '2025/26', 'tournament_stage_id': 'stage1'}
)

# Create teams
team1, _ = Team.objects.get_or_create(participant_id='TEST_T1', defaults={'name': 'Test Team 1', 'slug': 'test-team-1'})
team2, _ = Team.objects.get_or_create(participant_id='TEST_T2', defaults={'name': 'Test Team 2', 'slug': 'test-team-2'})

# Remove existing sample matches then create
Match.objects.filter(event_id__in=['TEST_M1','TEST_M2']).delete()
Match.objects.create(
    event_id='TEST_M1', season=season, round='1',
    home_team=team1, away_team=team2,
    home_event_participant_id=team1.participant_id, away_event_participant_id=team2.participant_id,
    start_time=timezone.now(), start_utime=0,
    event_stage='3', event_stage_id='3',
    home_score=2, away_score=1
)
Match.objects.create(
    event_id='TEST_M2', season=season, round='2',
    home_team=team2, away_team=team1,
    home_event_participant_id=team2.participant_id, away_event_participant_id=team1.participant_id,
    start_time=timezone.now(), start_utime=0,
    event_stage='3', event_stage_id='3',
    home_score=0, away_score=0
)

client = Client()
resp = client.get('/leagues/TEST_LEAGUE/table/')
print('table page status:', resp.status_code)
print('table page snippet:', resp.content[:500])
resp2 = client.get('/api/leagues/TEST_LEAGUE/seasons/')
print('seasons api status:', resp2.status_code)
print('seasons api content:', resp2.content[:200])
resp3 = client.get('/leagues/TEST_LEAGUE/table/partial/')
print('partial status:', resp3.status_code)
print('partial snippet:', resp3.content[:500])

