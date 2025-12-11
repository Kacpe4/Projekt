from django.shortcuts import render
from django.views import View

class HomePageView(View):
    def get(self, request):
        return render(request, 'core/home.html')
class MatchlistView(View):
    def get(self, request):
        return render(request, 'core/matchlist.html')