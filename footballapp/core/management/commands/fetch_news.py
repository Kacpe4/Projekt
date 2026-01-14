import feedparser
import ssl
from datetime import datetime
from time import mktime
from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils.timezone import make_aware

class Command(BaseCommand):
    help = 'Pobiera najnowsze newsy piłkarskie z BBC Sport.'

    def handle(self, *args, **options):
        # 1. Pobieramy model
        try:
            NewsArticle = apps.get_model('core', 'NewsArticle')
        except LookupError:
            self.stdout.write(self.style.ERROR("❌ Błąd: Nie znaleziono modelu NewsArticle."))
            return

        # 2. Fix dla Windowsa (częsty problem z certyfikatami SSL w Pythonie)
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context

        # 3. Lista źródeł (BBC Sport jest bardzo stabilne)
        RSS_URL = "https://feeds.bbci.co.uk/sport/football/rss.xml"

        self.stdout.write(f"📰 Łączę się z: BBC Sport...")
        
        # Pobieranie danych
        feed = feedparser.parse(RSS_URL)
        
        # Sprawdzenie czy coś przyszło
        count_entries = len(feed.entries)
        if count_entries == 0:
            self.stdout.write(self.style.ERROR(f"❌ Pusto! Serwer nic nie zwrócił. Status: {feed.get('status', 'nieznany')}"))
            return

        self.stdout.write(f"✅ Połączono! Znaleziono {count_entries} wpisów. Przetwarzam...")

        total_new = 0

        for entry in feed.entries:
            try:
                # Tytuł i Link
                title = entry.title
                link = entry.link
                summary = entry.get('summary', '')

                # Data publikacji
                if hasattr(entry, 'published_parsed'):
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    pub_date = make_aware(dt)
                else:
                    pub_date = make_aware(datetime.now())

                # Szukanie obrazka (BBC używa media_thumbnail)
                img_src = ""
                if 'media_thumbnail' in entry:
                    # BBC często daje kilka rozmiarów, bierzemy pierwszy (zazwyczaj największy)
                    img_src = entry.media_thumbnail[0]['url']
                
                # Jeśli wciąż pusto, szukamy w linkach
                if not img_src and 'links' in entry:
                    for l in entry.links:
                        if l.get('type', '').startswith('image/'):
                            img_src = l['href']
                            break

                # Zapis do bazy
                obj, created = NewsArticle.objects.update_or_create(
                    url=link,
                    defaults={
                        'title': title,
                        'description': summary,
                        'image_url': img_src,
                        'published_date': pub_date,
                        'source_name': "BBC Sport"
                    }
                )

                if created:
                    total_new += 1
                    self.stdout.write(f" + Dodano: {title[:30]}...")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Błąd przy artykule: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"🎉 GOTOWE! Pobrano {total_new} nowych artykułów."))