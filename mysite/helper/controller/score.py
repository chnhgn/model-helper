from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render


def index(request):
    context = None
    return render(request, 'helper/score_input.html', context)