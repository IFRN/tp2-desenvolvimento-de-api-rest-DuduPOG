import secrets
import hashlib
import qrcode
import io
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from urna.models import *
from urna.serializers import *

class EleitorViewSet(viewsets.ModelViewSet):
    queryset = Eleitor.objects.all()
    serializer_class = EleitorSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['ativo']
    search_fields = ['nome', 'email', 'cpf']
    ordering_fields = ['nome', 'data_cadastro']
    ordering = ['nome']


class EleicaoViewSet(viewsets.ModelViewSet):
    queryset = Eleicao.objects.all()
    serializer_class = EleicaoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'tipo', 'criada_por']
    search_fields = ['titulo']
    ordering_fields = ['data_inicio', 'data_fim', 'titulo']
    ordering = ['-data_inicio']
    


class CandidatoViewSet(viewsets.ModelViewSet):
    serializer_class = CandidatoSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['eleicao']
    search_fields = ['nome', 'nome_urna', 'partido_ou_chapa']
    ordering_fields = ['numero', 'nome']
    ordering = ['eleicao', 'numero']
    
    def get_queryset(self):
        return Candidato.objects.select_related('eleicao')


class AptidaoEleitorViewSet(viewsets.ModelViewSet):
    serializer_class = AptidaoEleitorSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['eleitor', 'eleicao']
    ordering_fields = ['data_inclusao']
    ordering = ['-data_inclusao']
    
    def get_queryset(self):
        return AptidaoEleitor.objects.select_related('eleitor', 'eleicao')


class RegistroVotacaoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RegistroVotacaoSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['eleicao']
    ordering_fields = ['data_hora']
    ordering = ['-data_hora']
    
    def get_queryset(self):
        return RegistroVotacao.objects.select_related('eleitor', 'eleicao')


class VotoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VotoSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['eleicao']
    ordering_fields = ['data_hora']
    ordering = ['-data_hora']
    
    def get_queryset(self):
        return Voto.objects.select_related('eleicao', 'candidato')
