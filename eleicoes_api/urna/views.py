import secrets
import hashlib
import qrcode
import io
from django.db import IntegrityError
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
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
    
    @action(detail=True, methods=['post'])
    def voto(self, request, pk=None):

        eleicao = self.get_object()
        
        if eleicao.status != 'aberta':
            return Response(
                {
                    'detail': 'O eleitor não pode votar em uma eleição não aberta'
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        
        serializer = VotacaoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        eleitor_id = serializer.validated_data['eleitor_id']
        candidato_id = serializer.validated_data.get('candidato_id')
        em_branco = serializer.validated_data.get('em_branco', False)
        
        eleitor = Eleitor.objects.get(id=eleitor_id)
        
        try:
            registro = RegistroVotacao.objects.create(eleitor=eleitor, eleicao=eleicao)
        except IntegrityError:
            return Response(
                {
                    'detail': 'Eleitor já votou nesta eleição.'
                },
                status=status.HTTP_409_CONFLICT
            )
        
        token = secrets.token_urlsafe(32)
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        dados_voto = {
            'eleicao': eleicao.id,
            'em_branco': em_branco,
            'comprovante_hash': token_hash,
        }
        
        if not em_branco:
            dados_voto['candidato'] = candidato_id
        
        voto = Voto.objects.create(**dados_voto)
        
        qr_data = f"/eleicoes_api/verificacao-comprovante/?token={token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        if em_branco:
            candidato_display = None
        else:
            candidato = Candidato.objects.get(id=candidato_id)
            candidato_display = f"{candidato.nome_urna} (#{candidato.numero})"
        
        resposta = {
            'mensagem': 'Voto registrado com sucesso. Guarde o seu comprovante.',
            'comprovante': {
                'token': token,
                'eleicao': eleicao.titulo,
                'candidato': candidato_display if not em_branco else 'BRANCO',
                'data_hora': voto.data_hora.isoformat(),
                'qr_code_url': f'/eleicoes_api/comprovantes/qr/?token={token}'
            }
        }
        
        return Response(resposta, status=status.HTTP_201_CREATED)


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

@api_view(['GET'])
def verificacao_comprovante(request):
    token = request.query_params.get('token')
    
    if not token:
        return Response(
            {
                'valido': False,
                'mensagem': 'Token não fornecido.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    try:
        voto = Voto.objects.select_related('eleicao', 'candidato').get(
            comprovante_hash=token_hash
        )
    except Voto.DoesNotExist:
        return Response(
            {
                'valido': False,
                'mensagem': 'Comprovante inválido.'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    if voto.em_branco:
        candidato_display = 'BRANCO'
    else:
        candidato_display = f"{voto.candidato.nome_urna} (#{voto.candidato.numero})"
    
    resposta = {
        'valido': True,
        'eleicao': voto.eleicao.titulo,
        'candidato': candidato_display,
        'data_hora': voto.data_hora.isoformat()
    }
    
    return Response(resposta, status=status.HTTP_200_OK)

@api_view(['GET'])
def gerar_qr_code(request):
    token = request.query_params.get('token')
    
    if not token:
        return Response(
            {'mensagem': 'Token não fornecido.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    qr_data = f"/eleicoes_api/verificacao-comprovante/?token={token}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    qr_image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return HttpResponse(buffer.getvalue(), content_type='image/png')
