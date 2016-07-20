from django.conf.urls import url
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'controller'))
import score
import model_import


urlpatterns = [
    url(r'^score/$', score.index, name='index'),
    url(r'^import/$', model_import.index, name='index'),
    url(r'^importing/$', model_import.importing, name='importing'),
]