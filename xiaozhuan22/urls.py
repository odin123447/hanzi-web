from django.urls import path
from . import views

app_name = 'xiaozhuan22'

urlpatterns = [
    path('UI', views.UI, name="UI"),
    path('convert', views.convert, name='convert'),
    path('historyUI', views.historyUI, name="historyUI"),
    path('delete', views.delete_history, name="delete"),
    path('export-word', views.export_word, name='export_word'),
    path('export-word-upload', views.export_word_upload, name='export_word_upload'),
]