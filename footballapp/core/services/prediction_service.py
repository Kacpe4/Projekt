"""
Serwis przewidywania wyników meczów piłkarskich
Używa machine learning do przewidywania wyników na podstawie historycznych danych
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from django.db.models import Avg, Count, Q
from ..models import Match, MatchStatistic, Team
from datetime import timedelta


class MatchPredictionService:
    """
    Serwis przewidywania wyników meczów.
    Przewiduje: wygrana gospodarzy (1), remis (X), wygrana gości (2)
    """

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def extract_team_features(self, team, last_n_matches=5):
        """
        Ekstraktuje cechy drużyny na podstawie ostatnich meczów
        """
        # Pobierz ostatnie mecze (zakończone)
        recent_matches = Match.objects.filter(
            Q(home_team=team) | Q(away_team=team),
            event_stage='3'  # Finished
        ).order_by('-start_time')[:last_n_matches]

        if not recent_matches:
            # Zwróć domyślne wartości jeśli brak danych
            return {
                'avg_goals_scored': 0.0,
                'avg_goals_conceded': 0.0,
                'win_rate': 0.0,
                'draw_rate': 0.0,
                'avg_possession': 50.0,
                'avg_shots_on_target': 0.0,
                'avg_xg': 0.0,
                'form': 0.0  # punkty z ostatnich meczów
            }

        goals_scored = []
        goals_conceded = []
        points = []
        possessions = []
        shots_on_target = []
        xg_values = []

        for match in recent_matches:
            is_home = match.home_team == team

            if is_home:
                scored = match.home_full_time_score or match.home_score or 0
                conceded = match.away_full_time_score or match.away_score or 0

                # Pobierz statystyki
                stats = MatchStatistic.objects.filter(match=match, period='match')
                possession = stats.filter(stat_name='Ball Possession').first()
                shots = stats.filter(stat_name='Shots on target').first()
                xg = stats.filter(stat_name='Expected Goals (xG)').first()

                if possession:
                    possessions.append(possession.home_value_numeric or 50.0)
                if shots:
                    shots_on_target.append(shots.home_value_numeric or 0.0)
                if xg:
                    xg_values.append(xg.home_value_numeric or 0.0)
            else:
                scored = match.away_full_time_score or match.away_score or 0
                conceded = match.home_full_time_score or match.home_score or 0

                # Pobierz statystyki
                stats = MatchStatistic.objects.filter(match=match, period='match')
                possession = stats.filter(stat_name='Ball Possession').first()
                shots = stats.filter(stat_name='Shots on target').first()
                xg = stats.filter(stat_name='Expected Goals (xG)').first()

                if possession:
                    possessions.append(possession.away_value_numeric or 50.0)
                if shots:
                    shots_on_target.append(shots.away_value_numeric or 0.0)
                if xg:
                    xg_values.append(xg.away_value_numeric or 0.0)

            goals_scored.append(scored)
            goals_conceded.append(conceded)

            # Punkty: 3 za wygraną, 1 za remis, 0 za przegraną
            if scored > conceded:
                points.append(3)
            elif scored == conceded:
                points.append(1)
            else:
                points.append(0)

        # Oblicz statystyki
        total_matches = len(recent_matches)
        wins = sum(1 for p in points if p == 3)
        draws = sum(1 for p in points if p == 1)

        return {
            'avg_goals_scored': np.mean(goals_scored) if goals_scored else 0.0,
            'avg_goals_conceded': np.mean(goals_conceded) if goals_conceded else 0.0,
            'win_rate': (wins / total_matches) if total_matches > 0 else 0.0,
            'draw_rate': (draws / total_matches) if total_matches > 0 else 0.0,
            'avg_possession': np.mean(possessions) if possessions else 50.0,
            'avg_shots_on_target': np.mean(shots_on_target) if shots_on_target else 0.0,
            'avg_xg': np.mean(xg_values) if xg_values else 0.0,
            'form': sum(points) / (total_matches * 3) if total_matches > 0 else 0.0
        }

    def prepare_match_features(self, home_team, away_team):
        """
        Przygotowuje cechy dla meczu między dwiema drużynami
        """
        home_features = self.extract_team_features(home_team)
        away_features = self.extract_team_features(away_team)

        # Kombinacja cech obu drużyn
        features = [
            home_features['avg_goals_scored'],
            home_features['avg_goals_conceded'],
            home_features['win_rate'],
            home_features['draw_rate'],
            home_features['avg_possession'],
            home_features['avg_shots_on_target'],
            home_features['avg_xg'],
            home_features['form'],
            away_features['avg_goals_scored'],
            away_features['avg_goals_conceded'],
            away_features['win_rate'],
            away_features['draw_rate'],
            away_features['avg_possession'],
            away_features['avg_shots_on_target'],
            away_features['avg_xg'],
            away_features['form'],
            # Różnice między drużynami
            home_features['avg_goals_scored'] - away_features['avg_goals_scored'],
            home_features['avg_goals_conceded'] - away_features['avg_goals_conceded'],
            home_features['form'] - away_features['form'],
        ]

        return np.array(features), home_features, away_features

    def train_model(self, min_matches=50):
        """
        Trenuje model na podstawie historycznych meczów
        """
        # Pobierz zakończone mecze z wynikami
        matches = Match.objects.filter(
            event_stage='3',  # Finished
            home_full_time_score__isnull=False,
            away_full_time_score__isnull=False
        ).order_by('-start_time')[:500]  # Ostatnie 500 meczów

        if len(matches) < min_matches:
            return False, f"Za mało danych treningowych. Znaleziono {len(matches)} meczów, wymagane minimum {min_matches}."

        X = []
        y = []

        for match in matches:
            features, _, _ = self.prepare_match_features(match.home_team, match.away_team)
            X.append(features)

            # Określ wynik: 1 (wygrana gospodarzy), 0 (remis), 2 (wygrana gości)
            home_score = match.home_full_time_score
            away_score = match.away_full_time_score

            if home_score > away_score:
                result = 1  # Wygrana gospodarzy
            elif home_score == away_score:
                result = 0  # Remis
            else:
                result = 2  # Wygrana gości

            y.append(result)

        X = np.array(X)
        y = np.array(y)

        # Normalizacja cech
        X_scaled = self.scaler.fit_transform(X)

        # Trenowanie modelu
        self.model.fit(X_scaled, y)
        self.is_trained = True

        return True, f"Model wytrenowany na {len(matches)} meczach."

    def predict_match(self, home_team, away_team):
        """
        Przewiduje wynik meczu między dwiema drużynami

        Returns:
            dict: {
                'prediction': str,  # '1', 'X', '2'
                'probabilities': dict,  # {'1': 0.5, 'X': 0.3, '2': 0.2}
                'confidence': float,  # 0-100
                'home_features': dict,
                'away_features': dict
            }
        """
        if not self.is_trained:
            success, message = self.train_model()
            if not success:
                return {
                    'error': message,
                    'prediction': None
                }

        # Przygotuj cechy
        features, home_features, away_features = self.prepare_match_features(home_team, away_team)
        features_scaled = self.scaler.transform([features])

        # Przewidywanie
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        # Mapowanie wyników
        result_map = {1: '1', 0: 'X', 2: '2'}
        prediction_label = result_map[prediction]

        # Prawdopodobieństwa dla każdego wyniku
        # Klasy w modelu: [0 (X), 1 (1), 2 (2)]
        classes = self.model.classes_
        prob_dict = {}
        for cls, prob in zip(classes, probabilities):
            prob_dict[result_map[cls]] = round(float(prob) * 100, 2)

        # Pewność predykcji (max prawdopodobieństwo)
        confidence = round(float(max(probabilities)) * 100, 2)

        return {
            'prediction': prediction_label,
            'probabilities': prob_dict,
            'confidence': confidence,
            'home_features': home_features,
            'away_features': away_features,
            'error': None
        }

    def get_upcoming_matches_predictions(self, limit=10):
        """
        Przewiduje wyniki nadchodzących meczów
        """
        upcoming = Match.objects.filter(
            event_stage='1'  # Scheduled
        ).order_by('start_time')[:limit]

        predictions = []
        for match in upcoming:
            prediction = self.predict_match(match.home_team, match.away_team)
            if not prediction.get('error'):
                predictions.append({
                    'match': match,
                    'prediction': prediction
                })

        return predictions

