from django.urls import path
from .views import StartDeepWorkView, StopDeepWorkView

urlpatterns = [
    path('deep-work/start/', StartDeepWorkView.as_view(), name='deep-work-start'),
    path('deep-work/stop/', StopDeepWorkView.as_view(), name='deep-work-stop'),
]
