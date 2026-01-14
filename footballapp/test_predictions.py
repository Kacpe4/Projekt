"""
Test serwisu przewidywania wyników meczów
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'footballapp.settings')
django.setup()

from core.services.prediction_service import MatchPredictionService
from core.models import Team, Match

def test_prediction_service():
    print("=" * 60)
    print("TEST SERWISU PRZEWIDYWANIA WYNIKÓW")
    print("=" * 60)
    
    # Sprawdź liczbę meczów w bazie
    total_matches = Match.objects.filter(event_stage='3').count()
    print(f"\n✓ Zakończone mecze w bazie: {total_matches}")
    
    if total_matches < 50:
        print("⚠ UWAGA: Za mało meczów do trenowania modelu (minimum 50)")
        return
    
    # Sprawdź liczbę drużyn
    total_teams = Team.objects.count()
    print(f"✓ Drużyny w bazie: {total_teams}")
    
    # Stwórz serwis
    print("\n" + "=" * 60)
    print("TRENOWANIE MODELU...")
    print("=" * 60)
    
    service = MatchPredictionService()
    success, message = service.train_model()
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ Błąd: {message}")
        return
    
    # Pobierz dwie drużyny do testu
    teams = Team.objects.all()[:2]
    if len(teams) < 2:
        print("✗ Za mało drużyn w bazie do testu")
        return
    
    home_team = teams[0]
    away_team = teams[1]
    
    print("\n" + "=" * 60)
    print(f"TEST PRZEWIDYWANIA: {home_team.name} vs {away_team.name}")
    print("=" * 60)
    
    # Przewiduj mecz
    prediction = service.predict_match(home_team, away_team)
    
    if prediction.get('error'):
        print(f"✗ Błąd: {prediction['error']}")
        return
    
    print(f"\n📊 WYNIKI PRZEWIDYWANIA:")
    print(f"   Przewidywany wynik: {prediction['prediction']}")
    print(f"   Pewność: {prediction['confidence']}%")
    print(f"\n📈 PRAWDOPODOBIEŃSTWA:")
    for outcome, prob in prediction['probabilities'].items():
        label = {
            '1': 'Wygrana gospodarzy',
            'X': 'Remis',
            '2': 'Wygrana gości'
        }[outcome]
        print(f"   {label} ({outcome}): {prob}%")
    
    print(f"\n⚽ STATYSTYKI GOSPODARZY ({home_team.name}):")
    for key, value in prediction['home_features'].items():
        print(f"   {key}: {value:.2f}")
    
    print(f"\n⚽ STATYSTYKI GOŚCI ({away_team.name}):")
    for key, value in prediction['away_features'].items():
        print(f"   {key}: {value:.2f}")
    
    # Test przewidywań dla nadchodzących meczów
    print("\n" + "=" * 60)
    print("PRZEWIDYWANIA DLA NADCHODZĄCYCH MECZÓW")
    print("=" * 60)
    
    upcoming_predictions = service.get_upcoming_matches_predictions(limit=5)
    
    if not upcoming_predictions:
        print("⚠ Brak nadchodzących meczów w bazie")
    else:
        print(f"\n✓ Znaleziono {len(upcoming_predictions)} nadchodzących meczów\n")
        for i, item in enumerate(upcoming_predictions, 1):
            match = item['match']
            pred = item['prediction']
            print(f"{i}. {match.home_team.name} vs {match.away_team.name}")
            print(f"   Przewidywanie: {pred['prediction']} (pewność: {pred['confidence']}%)")
            print(f"   Data: {match.start_time.strftime('%Y-%m-%d %H:%M')}")
            print()
    
    print("=" * 60)
    print("✓ TEST ZAKOŃCZONY POMYŚLNIE!")
    print("=" * 60)

if __name__ == '__main__':
    test_prediction_service()

