from django.urls import path

from .views import LeaderboardView, MyKarmaView

urlpatterns = [
    path('me/', MyKarmaView.as_view(), name='karma_me'),
    path('leaderboard/', LeaderboardView.as_view(), name='karma_leaderboard'),
]
