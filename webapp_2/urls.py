"""
URL configuration for webapp_2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include

import jianfan22


def home(request):
    return render(request, 'home.html')

def evolution(request):
    return render(request, 'evolution.html')

def historycenter(request):
    return render(request, 'history_center.html')
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('evolution/', evolution, name='evolution'),
    path('historycenter', historycenter, name='historycenter'),
    path('jianfan22/', include('jianfan22.urls')),
    path('xiaozhuan22/', include('xiaozhuan22.urls')),
]
