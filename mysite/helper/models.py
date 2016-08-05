from django.db import models

# Create your models here.
class Model_Main(models.Model):
    id = models.AutoField(primary_key=True)
    model_Id = models.CharField(max_length=40)
    model_Name = models.CharField(max_length=30)
    file_Name = models.CharField(max_length=30, default='null')
    model_File = models.TextField()
    output_prob_var = models.CharField(max_length=30, default='null')
