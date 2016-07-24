from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render
from helper.models import Model_Main
from django.db import connection


def index(request):
    # Retrieve the model list
    cursor = connection.cursor()
    cursor.execute("select model_Id, model_Name from helper_model_main group by model_Id, model_Name")
    models = cursor.fetchall()
    return render(request, 'helper/score_input.html', {'models' : models})

def scoring(request):
    pass