from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_notifications, name='notification_list'),
    path('read-all/', views.mark_all_notifications_read, name='notifications_read_all'),
    path('<uuid:notification_id>/read/', views.mark_notification_read, name='notification_read'),
]
