from django.conf.urls import url
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'controller'))
import score


urlpatterns = [
    url(r'^score/$', score.index, name='index'),
]