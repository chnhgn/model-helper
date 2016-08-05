from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import loader
from django.shortcuts import render
import zipfile, os, io
import shutil
from django.db import transaction
from django.db import connection
import sys
from helper.models import Model_Main
import uuid
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import score


def index(request):
    cursor = connection.cursor()
    cursor.execute("select model_Id, model_Name from helper_model_main group by model_Id, model_Name")
    models = cursor.fetchall()
    cursor.close()
    return render(request, 'helper/import.html', {'models' : models})

def importing(request):
    """
        Currently only support sas spk model import, 
        extracting the model files and then save them to database.
        In order not to get the performance so bad, need to save the data in memory then commit to database.
    """
    try:
        # create a directory to store the model files
        model_files_dir = "model_files"
        os.mkdir(model_files_dir)
        
        zip_file = zipfile.ZipFile(request.FILES['model_path'], mode='r')
        for file in zip_file.namelist():
            # extract sas files
            if str(file) == 'PATHSCORE.spk':
                inner_zip = io.BytesIO(zip_file.read(file))
                zip2 = zipfile.ZipFile(inner_zip)
                for file2 in zip2.namelist():
                    if str(file2) == 'SASSCORE.spk':
                        score_spk = io.BytesIO(zip2.read(file2))
                        zip3 = zipfile.ZipFile(score_spk)
                        for i in zip3.namelist():
                            zip3.extract(i, model_files_dir)
                            
            # extract mining result files
            if str(file) == 'MININGRESULT.spk':
                inner_zip = io.BytesIO(zip_file.read(file))
                zip2 = zipfile.ZipFile(inner_zip)
                for i in zip2.namelist():
                    zip2.extract(i, model_files_dir)
        
        # Save the model files to database
        model_uuid = uuid.uuid1()     # id to specify the model
        files = os.listdir(model_files_dir)     
        for f in files:
            with open(model_files_dir + '/' + f, 'r') as s:
                data = s.read()
                entry = Model_Main(model_Id=model_uuid, model_Name=str(request.FILES['model_path']), file_Name= str(f), model_File=data)
                entry.save()
                 
        transaction.commit()      # commit the memory result to database  
                   
    finally:
        shutil.rmtree(model_files_dir)
            
    return HttpResponse('The model was imported successfully.')

def detail(request):
    model_id = request.GET.get('modelId')
    try:
        # Fetch the model input/output
        cursor = connection.cursor()
        cursor.execute("select model_File from helper_model_main where model_Id = '%s' and file_Name = '%s'" % (model_id, 'input.xml'))
        model_input_xml = cursor.fetchone()[0]
        model_input_vars = score.parse_columns_from_xml(model_input_xml, 'INPUT')
        inputVars = []
        for i in range(len(model_input_vars['columns'])):
            entry = (model_input_vars['columns'][i], model_input_vars['types'][i])
            inputVars.append(entry)
        
        cursor.execute("select model_File from helper_model_main where model_Id = '%s' and file_Name = '%s'" % (model_id, 'output.xml'))
        model_output_xml = cursor.fetchone()[0]
        model_output_vars = score.parse_columns_from_xml(model_output_xml, 'OUTPUT')
        outputVars, outputEventVars = [], []
        for i in range(len(model_output_vars['columns'])):
            entry = (model_output_vars['columns'][i], model_output_vars['types'][i])
            outputVars.append(entry)
            if model_output_vars['types'][i] == 'number':   # all the numeric variables in output list should be the candidates for output event
                outputEventVars.append(model_output_vars['columns'][i])
        
        # Fetch output event variable
        cursor.execute("select output_prob_var from helper_model_main where model_Id = '%s' and file_Name like '%s'" % (model_id, '%score.sas'))
        prob_var = cursor.fetchone()[0]
        if prob_var == 'null':
            prob_var = ''
        
    finally:
        cursor.close()
    return render(request, 'helper/model_detail.html', {'inputVars':inputVars, 'outputVars':outputVars, 'model_id':model_id, 'outputEventVars':outputEventVars, 'prob_var':prob_var})

def modify(request):
    model_id = request.POST.get('modelId')
    output_event_var = request.POST.get('output_event_var')
    try:
        cursor = connection.cursor()
        cursor.execute("update helper_model_main set output_prob_var = '%s' where model_Id = '%s' and file_Name like '%s'" % (output_event_var, model_id, '%score.sas'))
        connection.commit()
    finally:
        cursor.close()
    
    return HttpResponseRedirect('/helper/import')

def searchFile(source, target):
    zip_file = zipfile.ZipFile(source, mode='r')  # load the model to memory
    for file in zip_file.namelist():
        if str(file).endswith('.spk'):
            if str(file) == target:
                inner_zip = io.BytesIO(zip_file.read(file))
                zip2 = zipfile.ZipFile(inner_zip)
                print(zip2.namelist())
                return zip2
            else:
                inner_zip = io.BytesIO(zip_file.read(file))
                return searchFile(inner_zip, target)

                
                
                
                
                
                
                
                
                