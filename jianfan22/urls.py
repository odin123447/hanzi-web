from django.urls import path
from . import views

app_name = 'jianfan22'

urlpatterns = [
    path('convert', views.convert, name='convert'),
    path('UI', views.UI, name="UI"),
    path('historyUI', views.historyUI, name="historyUI"),
    path('delete', views.delete_history, name="delete"),
]