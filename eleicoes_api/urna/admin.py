from django.contrib import admin
from urna.models import *

# Register your models here.

admin.site.register(Eleitor)
admin.site.register(Eleicao)
admin.site.register(Candidato)
admin.site.register(AptidaoEleitor)
admin.site.register(RegistroVotacao)
admin.site.register(Voto)