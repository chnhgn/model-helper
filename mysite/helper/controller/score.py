from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render
from helper.models import Model_Main
from django.db import connection
from sas7bdat import SAS7BDAT
from xml.etree import ElementTree as ET



def index(request):
    """
    initialize the scoring page
    """
    # Retrieve the model list
    cursor = connection.cursor()
    cursor.execute("select model_Id, model_Name from helper_model_main group by model_Id, model_Name")
    models = cursor.fetchall()
    return render(request, 'helper/score_input.html', {'models' : models})

def scoring(request):
    """
    Collect the model information and input table prior to the mapping procedure
    """
    in_table_path = request.POST.get('score_input')
    out_table_path = request.POST.get('score_output')
    model_id = request.POST.get('model_id')
    
    # Fetch the model input/output
    cursor = connection.cursor()
    cursor.execute("select model_File from helper_model_main where model_Id = '%s' and file_Name = '%s'" % (model_id, 'input.xml'))
    input_xml = cursor.fetchone()[0]
    model_info = parse_columns_from_xml(input_xml)
    initial_mapping = []
    with SAS7BDAT(in_table_path) as f:
        target_vars = []
        for item in f.column_names:
            name = item.decode('utf-8')
            target_vars.append(name)
            
        # If the name and data type are the same, the variables should be mapped automatically
        for i in range(len(model_info['columns'])):
            arr = []
            arr.append(model_info['columns'][i])
            for j in range(len(f.column_names)):
                name = f.column_names[j].decode('utf-8')
                if model_info['columns'][i] == name and model_info['types'][i] == f.column_types[j]:
                    arr.append(name)
                    break
            
            initial_mapping.append(arr)    
        
    return render(request, 'helper/score_mapping.html', 
                  {'in_table_path' : in_table_path, 'out_table_path' : out_table_path, 'initial_mapping' : initial_mapping, 'target_vars' : target_vars})

def execute(request):
    """
    Generate score code then executing the scoring task in SAS Foundation
    """
    return render(request, 'helper/score_result.html', None)

def parse_columns_from_xml(source):
    column_names, column_types = [], []
    root = ET.fromstring(source)
    elements = root.findall('INPUT')
    for el in elements:
        columns = el.findall('COLUMN')
        for col in columns:
            if col.attrib.get('name') == 'NAME':
                column_names.append(col.attrib.get('value'))
            if col.attrib.get('name') == 'TYPE':
                if col.attrib.get('value') == 'N':
                    column_types.append('number')
                if col.attrib.get('value') == 'C':
                    column_types.append('string')
        
    model_info = {'columns' : column_names, 'types' : column_types}
    return model_info
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        