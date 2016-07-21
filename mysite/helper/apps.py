from django.apps import AppConfig
from django.db.models.signals import post_save

class HelperConfig(AppConfig):
    name = 'helper'
    verbose_name = 'helper'
    
#     def ready(self):
#         from .signals import someSignal
#         post_save.connect(
#             receiver=someSignal,
#             sender=self.get_model('Model_Main')
#         )