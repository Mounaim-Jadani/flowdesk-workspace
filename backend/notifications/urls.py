from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_notifications, name='notification_list'),
    path('<uuid:notification_id>/read/', views.mark_notification_read, name='notification_read'),
]
