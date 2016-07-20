from django.db import models
import uuid

# Create your models here.
class Models(models.Model):
    id = models.AutoField(primary_key=True)
    model_Id = models.CharField(max_length=16)
    model_Name = models.CharField(max_length=50)
    model_File = models.TextField()
    