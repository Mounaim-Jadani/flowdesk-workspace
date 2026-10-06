from django.urls import path
from .views import DigestRoomView, DigestConsumeView

urlpatterns = [
    path('rooms/<str:room_id>/', DigestRoomView.as_view(), name='room-digest'),
    path('rooms/<str:room_id>/consume/', DigestConsumeView.as_view(), name='room-digest-consume'),
]
