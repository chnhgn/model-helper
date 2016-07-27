from django.http import HttpResponse
from django.template import loader, Context, Template
from django.shortcuts import render
from helper.models import Model_Main
from django.db import connection
from sas7bdat import SAS7BDAT
from xml.etree import ElementTree as ET
import os
import shutil



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
    model_input_xml = cursor.fetchone()[0]
    model_input_vars = parse_columns_from_xml(model_input_xml, 'INPUT')
    
    cursor.execute("select model_File from helper_model_main where model_Id = '%s' and file_Name = '%s'" % (model_id, 'output.xml'))
    model_output_xml = cursor.fetchone()[0]
    model_output_vars = parse_columns_from_xml(model_output_xml, 'OUTPUT')
    cursor.close()
    
    # Mapping variables need both model input variables and output variables
    columns, types = [], []
    model_vars = {'columns' : columns, 'types' : types}  
    for i in range(len(model_output_vars['columns'])):
        columns.append(model_output_vars['columns'][i])
        types.append(model_output_vars['types'][i])
        for j in range(len(model_input_vars['columns'])):
            if model_output_vars['columns'][i] == model_input_vars['columns'][j] and model_output_vars['types'][i] == model_input_vars['types'][j]:
                continue
            else:
                if model_input_vars['columns'][j] not in model_vars['columns']:
                    columns.append(model_input_vars['columns'][j])
                types.append(model_input_vars['types'][j])
                
    initial_mapping = []
    with SAS7BDAT(out_table_path) as f:
            
        # If the name and data type are the same, the variables should be mapped automatically
        for i in range(len(f.column_names)):
            name = f.column_names[i].decode('utf-8')
            arr = []
            arr.append(name)
            for j in range(len(model_vars['columns'])):
                if name == model_vars['columns'][j] and f.column_types[i] == model_vars['types'][j]:
                    arr.append(model_vars['columns'][j])
                    break
            
            initial_mapping.append(arr)    
        
    return render(request, 'helper/score_mapping.html', 
                  {'in_table_path' : in_table_path, 'out_table_path' : out_table_path,
                    'initial_mapping' : initial_mapping, 'target_vars' : model_vars['columns'], 'model_id' : model_id})

def execute(request):
    """
    Generate score code then executing the scoring task in SAS Foundation
    """
    input_table = request.POST.get('in_table')
    output_table = request.POST.get('out_table')
    model_id = request.POST.get('model_id')
    pairs_num = request.POST.get('pairs_num')
    mapping = {}
    for i in range(1, eval(pairs_num)+1):
        output_var = request.POST.get('output_var_' + str(i))
        map_var = request.POST.get('map_var_' + str(i))
        mapping[output_var] = map_var
        
    score_code = generate_score_code(input_table, output_table, model_id, mapping)
    try:
        temp_dir = 'tmp_sas'
        os.mkdir(temp_dir)
        with open(temp_dir + '/scoreTask.sas', 'w') as f:
            for code in score_code:
                f.write(code)
                f.write('\n')
        tmp_abs_dir = os.path.abspath(temp_dir)    
        # Execute the sas file
        os.chdir(temp_dir)
        os.system('sas scoreTask.sas')
        os.chdir('..')
        with open(temp_dir + '/score_result.html', 'r') as f:
            context = f.read()
                
    finally:
        shutil.rmtree(temp_dir)
        
    return HttpResponse(context)

def generate_score_code(in_table, out_table, model_id, mapping):
    """
    Generate the sas code which is used for scoring task
    """
    sas_code = []   # Use list to record the code
    
    # Create sas library for input/output table
    in_table_dir = os.path.dirname(in_table)
    out_table_dir = os.path.dirname(out_table)
    sas_code.append('libname data_lib base ("%s" "%s");' % (in_table_dir, out_table_dir))
    
    # Specify macro variables
    sas_code.append('%let _InputDs = data_lib.' + os.path.splitext(os.path.basename(in_table))[0] + ';')
    sas_code.append('%let _OutputDs = data_lib.' + os.path.splitext(os.path.basename(out_table))[0] + ';')
    
    # Generate map code
    code1, code2 = '', ''
    for key in mapping:
        code1 += '%s = %s;' % (key, mapping[key])
        code2 += '%s ' % key
    code = code1 + 'keep ' + code2 + ';'
    
    # Data step and model score code
    cursor = connection.cursor()
    cursor.execute("select model_File from helper_model_main where model_Id = '%s' and file_Name like '%s'" % (model_id, '%score.sas'))
    score_code = cursor.fetchall()[0]
    cursor.close()
    
    sas_code.append('ods listing close;')
    sas_code.append("ods html file='score_result.html';")
    sas_code.append('data &_OutputDs;')
    sas_code.append('set &_InputDs;')
    sas_code.append(score_code[0])
    sas_code.append(code)
    sas_code.append('run;')
    sas_code.append('title "Univariate for the numerical variables";')
    sas_code.append('proc univariate;run;')
    
    return sas_code

def parse_columns_from_xml(source, p_type):
    column_names, column_types = [], []
    root = ET.fromstring(source)
    if p_type == 'INPUT':
        elements = root.findall('INPUT')
    if p_type == 'OUTPUT':
        elements = root.findall('OUTPUT')    
        
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
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        