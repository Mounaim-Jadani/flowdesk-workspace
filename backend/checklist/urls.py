from django.urls import path
from . import views

urlpatterns = [
    path('items/', views.create_item, name='create_item'),
    path('rooms/<uuid:room_id>/items/', views.list_items, name='list_items'),
    path('items/<uuid:item_id>/', views.patch_item, name='patch_item'),
    path('items/<uuid:item_id>/done/', views.mark_item_done, name='mark_item_done'),
    path('items/<uuid:item_id>/dismiss/', views.dismiss_item, name='dismiss_item'),
]
