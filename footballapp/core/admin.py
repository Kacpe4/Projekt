from django.contrib import admin
from .models import Team, Player, Match, MatchStatistic

# Register your models here.
admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Match)
admin.site.register(MatchStatistic)
