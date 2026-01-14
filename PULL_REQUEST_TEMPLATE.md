## Podsumowanie zmian

Ten Pull Request łączy zmiany z brancha `kacper` do `main` i dodaje następujące funkcjonalności:

### ✨ Nowe funkcje:
- **System newsów piłkarskich** - pobieranie aktualności z BBC Sport RSS
- **System autentykacji** - logowanie, rejestracja, wylogowanie użytkowników
- **Zabezpieczenie widoków** - dostęp do meczów i drużyn tylko dla zalogowanych użytkowników
- **Nowe komendy Django:**
  - `fetch_initial_data.py` - inicjalizacja bazy (liga, sezon, drużyny, mecze)
  - `fetch_news.py` - pobieranie newsów z BBC Sport
  - Ulepszona `fetch_players.py` - lepsza obsługa nazw drużyn z aliasami

### 🔧 Poprawki kodu:
- Naprawione błędy w importach (spacje w `django. contrib`)
- Poprawione wcięcia i formatowanie
- Dodane komentarze w kodzie

### 📁 Nowe pliki:
- Model `NewsArticle` w `models.py`
- Szablony: `login.html`, `signup.html`, `news_list.html`, `base.html`
- Konfiguracja URL dla autentykacji
- Style CSS dla logowania

### 🗃️ Zmiany w bazie danych:
- Nowa migracja `0002_newsarticle.py`

Wszystko jest gotowe do merge!