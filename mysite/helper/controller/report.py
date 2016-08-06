from django.template import loader
from django.http import HttpResponse
from django.shortcuts import render
from django.db import connection
import os
import shutil



def index(request):
    return render(request, 'helper/report_main.html', None)

def distributeReport(request):
    reportId = request.POST.get('reportId')
    try:
        cursor = connection.cursor()
        cursor.execute("select model_Id, model_Name from helper_model_main group by model_Id, model_Name")
        models = cursor.fetchall()
    finally:
        cursor.close()
        
    if reportId == 'lift':
        return render(request, 'helper/lift_report.html', {'models' : models})
        
def generateLift(request):
    input_ds = request.POST.get('input_ds')        
    target = request.POST.get('target') 
    models = request.POST.getlist('model_list[]')
    execute_code = []
    try:
        cursor = connection.cursor()
        temp_dir = "tmp_report"
        os.mkdir(temp_dir)
        shutil.copy(input_ds, temp_dir)     # copy input data source to temp folder
        
        # code part 1
        sas_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sas')
        with open(os.path.join(sas_folder, 'lift_report_macro.sas'), 'r') as f:
            content = f.read()
            execute_code.append(content)
        execute_code.append('ods listing close;')
        execute_code.append('ods pdf file="lift_report.pdf";')    
        execute_code.append("libname ds '"+os.path.abspath(temp_dir)+"';")
        execute_code.append("%let score_input=ds."+os.path.splitext(os.path.basename(input_ds))[0]+";")
        execute_code.append("%let target="+target+";")
        
        for model_id in models:
            cursor.execute("select model_Name,file_Name,model_File,output_prob_var from helper_model_main where model_Id = '%s' and file_Name like '%s'" % (model_id, '%score.sas'))
            row = cursor.fetchone()
            if row[3] == 'null':
                return HttpResponse('All the selected models should have mapped the output event variable!')
            model_name = row[0]
            prob_var = row[3]
            with open(temp_dir + '/'+model_name+'_score.sas', 'w') as f:
                f.write(row[2])
            os.chdir(temp_dir)
            score_path = os.path.abspath(model_name+'_score.sas')   
            os.chdir('..')
            # code part 2
            execute_code.append("%precondition(score_code='"+score_path+"', event_prob=%s);" % prob_var)
            execute_code.append("%exec(name='"+model_name+"');") 
        
        # code part 3 
        execute_code.append("%plot;%gc;")
        
        # save the runnable code to the temp folder
        with open(temp_dir+'/taskCode.sas', 'w') as f:
            for code in execute_code:
                f.write(code)
        
        # execute the task code to generate the report
        os.chdir(temp_dir)
        os.system('sas taskCode.sas')
        os.chdir('..')
        # load the report file
        pdf = open(temp_dir + '/lift_report.pdf', 'rb').read()
            
    finally:
        cursor.close()
        shutil.rmtree(temp_dir)
    
    return HttpResponse(pdf, content_type='application/pdf')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    