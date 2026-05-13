"""
URL configuration for eleicoes_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from urna.views import *

router = DefaultRouter()
router.register(r'eleitores', EleitorViewSet, basename='eleitor')
router.register(r'eleicoes', EleicaoViewSet, basename='eleicao')
router.register(r'candidatos', CandidatoViewSet, basename='candidato')
router.register(r'aptidoes', AptidaoEleitorViewSet, basename='aptidao')
router.register(r'registros-votacao', RegistroVotacaoViewSet, basename='registro-votacao')
router.register(r'votos', VotoViewSet, basename='voto')

schema_view = get_schema_view(
    openapi.Info(
        title="API de Eleições",
        default_version='v1',
        description="API RESTful para Sistema de Gerenciamento de Eleições",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('eleicoes_api/', include(router.urls)),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
