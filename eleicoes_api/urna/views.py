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
    def abertura(self, request, pk=None):
        eleicao = self.get_object()
        
        if eleicao.status != 'rascunho':
            return Response(
                {
                    "detail": "Esta eleição não pode ser aberta, pois seu status não é rascunho."
                },
                status=status.HTTP_400_BAD_REQUEST
                )
        
        if eleicao.candidatos.count() < 2:
            return Response(
                {
                    "detail": "A eleição deve ter pelo menos 2 candidatos."
                },
                status=status.HTTP_400_BAD_REQUEST
                )
            
        if eleicao.aptos.count() < 1: # [cite: 214]
            return Response(
                {
                    "detail": "A eleição deve ter pelo menos 1 eleitor apto."
                },
                status=status.HTTP_400_BAD_REQUEST
                )
        
        eleicao.status = 'aberta'
        eleicao.save()
        
        serializer = self.get_serializer(eleicao)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def encerramento(self, request, pk=None):
        eleicao = self.get_object()
        
        if eleicao.status != 'aberta':
            return Response(
                {
                    "detail": "Apenas eleições abertas podem ser encerradas."
                },
                status=status.HTTP_400_BAD_REQUEST
                )
        
        eleicao.status = 'encerrada'
        eleicao.save()
        return Response(
            {
                "mensagem": "Eleição encerrada com sucesso."
            }
            )

    @action(detail=True, methods=['get'])
    def apuracao(self, request, pk=None):
        eleicao = self.get_object()
        
        if eleicao.status not in ['encerrada', 'apurada']:
            return Response(
                {
                    "detail": "Apuração permitida apenas para eleições encerradas ou apuradas."
                },
                status=status.HTTP_403_FORBIDDEN
                )

        total_aptos = eleicao.aptos.count() 
        total_votantes = eleicao.registros_votacao.count()
        total_abstencoes = total_aptos - total_votantes
        
        votos_validos = Voto.objects.filter(eleicao=eleicao, em_branco=False).count()
        votos_brancos = Voto.objects.filter(eleicao=eleicao, em_branco=True).count()
        
        resultados = []
        candidatos = eleicao.candidatos.all()
        for cand in candidatos:
            votos_cand = Voto.objects.filter(candidato=cand).count()
            percentual = (votos_cand / votos_validos * 100) if votos_validos > 0 else 0
            resultados.append({
                "candidato": cand.nome_urna,
                "numero": cand.numero,
                "votos": votos_cand,
                "percentual": round(percentual, 2)
            })
        
        resultados.sort(key=lambda x: x['votos'], reverse=True)
        max_votos = resultados[0]['votos'] if resultados else 0
        vencedores = [r['candidato'] for r in resultados if r['votos'] == max_votos and max_votos > 0]
        
        
        if eleicao.status == 'encerrada':
            eleicao.status = 'apurada'
            eleicao.save()

        return Response({
            "eleicao": eleicao.titulo,
            "total_aptos": total_aptos,
            "total_votantes": total_votantes,
            "total_abstencoes": total_abstencoes,
            "votos_validos": votos_validos,
            "votos_brancos": votos_brancos,
            "resultado": resultados,
            "vencedores": vencedores,
            "houve_empate": len(vencedores) > 1
        })

    @action(detail=True, methods=['get'])
    def votantes(self, request, pk=None):
        eleicao = self.get_object()
        compareceu_param = request.query_params.get('compareceu', 'true').lower() == 'true'
        
        if compareceu_param:
            registros = RegistroVotacao.objects.filter(eleicao=eleicao).select_related('eleitor')
            dados = [
                {
                    "nome": r.eleitor.nome,
                    "cpf": f"***.{r.eleitor.cpf[4:11]}-**",
                    "data_hora": r.data_hora
                }
                for r in registros
            ]
        else:
            votantes_ids = RegistroVotacao.objects.filter(eleicao=eleicao).values_list('eleitor_id', flat=True)
            abstencoes = AptidaoEleitor.objects.filter(eleicao=eleicao).exclude(eleitor_id__in=votantes_ids).select_related('eleitor')
            dados = [
                {
                "nome": a.eleitor.nome,
                "cpf": f"***.{a.eleitor.cpf[4:11]}-**"
                }
                for a in abstencoes
            ]

        return Response(dados)

    @action(detail=True, methods=['post'], url_path='cadastro-aptos')
    def cadastro_aptos(self, request, pk=None):
        eleicao = self.get_object()
        
        if eleicao.status != 'rascunho':
            return Response(
                {
                    "detail": "Cadastro de aptos permitido apenas em rascunho."
                },
                status=status.HTTP_400_BAD_REQUEST
                )
        
        eleitores_ids = request.data.get('eleitores_ids', [])
        cadastrados = 0
        
        with transaction.atomic():
            for eid in eleitores_ids:
                eleitor = Eleitor.objects.get(id=eid)
                if not AptidaoEleitor.objects.filter(eleicao=eleicao, eleitor=eleitor).exists():
                    AptidaoEleitor.objects.create(eleicao=eleicao, eleitor=eleitor)
                    cadastrados += 1
                    
        return Response({"total_cadastrados": cadastrados}, status=status.HTTP_201_CREATED)
    
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
