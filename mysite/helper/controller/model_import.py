from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render
import zipfile, os, io
import shutil


def index(request):
    context = None
    return render(request, 'helper/import.html', context)

def importing(request):
    
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
                
                    
    finally:
        shutil.rmtree(model_files_dir)
            
    return HttpResponse('The model was imported successfully.')

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

                
                
                
                
                
                
                
                
                
                