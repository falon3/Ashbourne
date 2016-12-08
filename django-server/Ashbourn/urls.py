"""Ashbourn URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, patterns, include
from django.contrib import admin
from . import views
import settings


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^map/', views.map_view),
    url(r'^add_record/', views.add_record_view, name='FirstMap-index'),
    url(r'^get_info/', views.test_get_info),
    url(r'^website/', views.show_report_home),
    url(r'^get_people_table/', views.show_person_table),
    url(r'^get_relations_table/', views.show_relations_table)
]
