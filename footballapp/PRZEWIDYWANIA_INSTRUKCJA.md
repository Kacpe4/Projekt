# 🔮 System Przewidywania Wyników Meczów - Instrukcja

## Opis projektu

Do aplikacji piłkarskiej został dodany **system przewidywania wyników meczów** wykorzystujący machine learning (scikit-learn). Model przewiduje wyniki meczów na podstawie historycznych danych i statystyk drużyn.

## Co zostało dodane?

### 1. Model Machine Learning
- **Lokalizacja**: `core/services/prediction_service.py`
- **Algorytm**: Random Forest Classifier (100 drzew decyzyjnych)
- **Przewidywane wyniki**: 
  - `1` - Wygrana gospodarzy
  - `X` - Remis
  - `2` - Wygrana gości

### 2. Cechy (Features) używane przez model

Model analizuje następujące statystyki dla obu drużyn (ostatnie 5 meczów):
- Średnia liczba strzelonych goli
- Średnia liczba straconych goli
- Procent wygranych meczów
- Procent remisów
- Średnie posiadanie piłki (%)
- Średnia liczba strzałów celnych
- Średnie Expected Goals (xG)
- Forma drużyny (punkty z ostatnich meczów)
- Różnice między drużynami w tych statystykach

### 3. Nowe widoki w aplikacji

#### a) **Przewidywania nadchodzących meczów**
- **URL**: `/predictions/`
- **Opis**: Automatycznie przewiduje wyniki wszystkich zaplanowanych meczów
- **Funkcjonalność**: 
  - Wyświetla top 20 nadchodzących meczów
  - Pokazuje przewidywany wynik
  - Pokazuje prawdopodobieństwa wszystkich możliwych wyników
  - Wyświetla poziom pewności predykcji

#### b) **Własny wybór drużyn**
- **URL**: `/predictions/custom/`
- **Opis**: Pozwala wybrać dowolne dwie drużyny i przewidzieć wynik meczu między nimi
- **Funkcjonalność**:
  - Formularz wyboru gospodarzy i gości
  - Szczegółowe statystyki obu drużyn
  - Przewidywany wynik z prawdopodobieństwami
  - Analiza formy i średnich statystyk

#### c) **Przewidywanie konkretnego meczu**
- **URL**: `/predictions/match/<match_id>/`
- **Opis**: Przewiduje wynik dla konkretnego meczu z bazy danych

### 4. Nowy link w nawigacji
W głównej nawigacji dodany został link **"🔮 Przewidywania"** prowadzący do systemu przewidywań.

## Jak używać?

### Uruchomienie aplikacji

1. **Zainstaluj wymagane pakiety**:
```bash
pip install -r requirements.txt
```

2. **Uruchom serwer Django**:
```bash
python manage.py runserver
```

3. **Otwórz aplikację w przeglądarce**:
```
http://127.0.0.1:8000/
```

4. **Kliknij "🔮 Przewidywania" w nawigacji**

### Pierwsze uruchomienie

Przy pierwszym wejściu na stronę przewidywań:
- Model automatycznie wytrenuje się na historycznych danych
- Potrzebne jest minimum 50 zakończonych meczów w bazie danych
- Proces trenowania zajmuje kilka sekund
- Model używa ostatnich 500 meczów jako dane treningowe

### Interpretacja wyników

**Przykładowy wynik przewidywania**:
```
Przewidywany wynik: 1
Pewność: 65%

Prawdopodobieństwa:
- Wygrana gospodarzy (1): 65%
- Remis (X): 20%
- Wygrana gości (2): 15%
```

**Co to oznacza?**
- Model przewiduje zwycięstwo gospodarzy
- Jest 65% pewny tej predykcji
- Istnieje 20% szans na remis i 15% na wygraną gości

## Jak to działa technicznie?

### 1. Ekstrakcja cech
```python
# Dla każdej drużyny pobierane są ostatnie 5 meczów
# Obliczane są statystyki:
- avg_goals_scored        # Średnia goli
- avg_goals_conceded      # Średnia straconych
- win_rate               # Procent wygranych
- draw_rate              # Procent remisów
- avg_possession         # Średnie posiadanie
- avg_shots_on_target    # Średnie strzały celne
- avg_xg                 # Średnie xG
- form                   # Forma (0-1)
```

### 2. Trenowanie modelu
```python
# Model trenuje się na historycznych meczach
# Używa RandomForestClassifier z 100 drzewami
# Dane są normalizowane (StandardScaler)
# Model zwraca klasę oraz prawdopodobieństwa
```

### 3. Przewidywanie
```python
service = MatchPredictionService()
prediction = service.predict_match(home_team, away_team)

# Zwraca:
{
    'prediction': '1',           # Przewidywany wynik
    'confidence': 65.5,          # Pewność %
    'probabilities': {           # Wszystkie prawdopodobieństwa
        '1': 65.5,
        'X': 20.3,
        '2': 14.2
    },
    'home_features': {...},      # Statystyki gospodarzy
    'away_features': {...}       # Statystyki gości
}
```

## Wymagania systemowe

### Zainstalowane pakiety:
- Django
- scikit-learn (machine learning)
- numpy (obliczenia numeryczne)
- pandas (opcjonalnie, dla manipulacji danymi)

### Dane w bazie:
- Minimum 50 zakończonych meczów (event_stage='3')
- Mecze z wypełnionymi wynikami (home_score, away_score)
- Opcjonalnie: statystyki meczów (posiadanie piłki, strzały, xG)

## Rozszerzenia i ulepszenia

### Możliwe usprawnienia:
1. **Więcej cech**:
   - Dodanie historii bezpośrednich starć (H2H)
   - Forma domowa vs wyjazdowa
   - Kontuzje/zawieszenia zawodników
   - Pora roku / pogoda

2. **Lepsze modele**:
   - Gradient Boosting (XGBoost, LightGBM)
   - Sieci neuronowe (TensorFlow/PyTorch)
   - Ensemble różnych modeli

3. **Przewidywanie dokładnego wyniku**:
   - Zamiast 1/X/2, przewidywanie np. 2-1, 0-0 itp.
   - Model regresji dla liczby goli

4. **Zapisywanie modelu**:
   - Zapisywanie wytrenowanego modelu do pliku (pickle)
   - Automatyczne aktualizowanie po nowych meczach

## Przykłady użycia w kodzie

### Przewidywanie dowolnego meczu
```python
from core.services.prediction_service import MatchPredictionService
from core.models import Team

# Pobierz drużyny
home_team = Team.objects.get(name="Manchester City")
away_team = Team.objects.get(name="Liverpool")

# Stwórz serwis i przewiduj
service = MatchPredictionService()
prediction = service.predict_match(home_team, away_team)

print(f"Przewidywany wynik: {prediction['prediction']}")
print(f"Pewność: {prediction['confidence']}%")
```

### Przewidywania dla wielu meczów
```python
service = MatchPredictionService()
predictions = service.get_upcoming_matches_predictions(limit=10)

for item in predictions:
    match = item['match']
    pred = item['prediction']
    print(f"{match.home_team.name} vs {match.away_team.name}")
    print(f"Przewidywanie: {pred['prediction']} ({pred['confidence']}%)")
```

## Wsparcie i rozwój

Model jest w pełni funkcjonalny i gotowy do użycia. W razie pytań lub problemów:
1. Sprawdź logi Django
2. Upewnij się, że baza zawiera wystarczająco dużo danych
3. Sprawdź czy wszystkie pakiety są zainstalowane

---

**Autor**: System AI
**Data utworzenia**: 2026-01-12
**Wersja**: 1.0

