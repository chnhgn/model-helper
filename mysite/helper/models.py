from django.db import models

# Create your models here.
class Model_Main(models.Model):
    id = models.AutoField(primary_key=True)
    model_Id = models.CharField(max_length=40)
    model_Name = models.CharField(max_length=30)
    model_File = models.TextField()
    
