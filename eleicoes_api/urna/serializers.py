from django.utils import timezone
from rest_framework import serializers
from urna.models import Eleitor, Eleicao, Candidato, AptidaoEleitor, RegistroVotacao, Voto
import re


class EleitorSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Eleitor
        fields = ['id', 'nome', 'email', 'cpf', 'data_nascimento', 'ativo', 'data_cadastro']
        read_only_fields = ['id', 'data_cadastro']
    
    def validate_cpf(self, value):
        pattern = r'^\d{3}\.\d{3}\.\d{3}-\d{2}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("CPF deve estar no formato 000.000.000-00")
        return value


class EleicaoSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()
    total_candidatos = serializers.SerializerMethodField()
    total_aptos = serializers.SerializerMethodField()
    
    class Meta:
        model = Eleicao
        fields = [
            'id', 'titulo', 'descricao', 'tipo', 'data_inicio', 'data_fim',
            'status', 'status_display', 'permite_branco', 'criada_por',
            'total_candidatos', 'total_aptos'
        ]
        read_only_fields = ['id', 'status_display', 'total_candidatos', 'total_aptos']
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    
    def get_total_candidatos(self, obj):
        return obj.candidatos.count()
    
    def get_total_aptos(self, obj):
        return obj.aptos.count()


class CandidatoSerializer(serializers.ModelSerializer):
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)
    
    class Meta:
        model = Candidato
        fields = [
            'id', 'eleicao', 'eleicao_titulo', 'numero', 'nome',
            'nome_urna', 'partido_ou_chapa', 'proposta', 'foto_url'
        ]
        read_only_fields = ['id', 'eleicao_titulo']
    
    def validate_numero(self, value):
        if value == 0:
            raise serializers.ValidationError("O número do candidato não pode ser zero (reservado para voto em branco)")
        return value


class AptidaoEleitorSerializer(serializers.ModelSerializer):
    eleitor_nome = serializers.CharField(source='eleitor.nome', read_only=True)
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)
    
    class Meta:
        model = AptidaoEleitor
        fields = [
            'id', 'eleitor', 'eleitor_nome', 'eleicao',
            'eleicao_titulo', 'data_inclusao'
        ]
        read_only_fields = ['id', 'eleitor_nome', 'eleicao_titulo', 'data_inclusao']


class RegistroVotacaoSerializer(serializers.ModelSerializer):
    eleitor_nome = serializers.CharField(source='eleitor.nome', read_only=True)
    eleicao_titulo = serializers.CharField(source='eleicao.titulo', read_only=True)
    
    class Meta:
        model = RegistroVotacao
        fields = [
            'id', 'eleitor', 'eleitor_nome', 'eleicao',
            'eleicao_titulo', 'data_hora'
        ]
        read_only_fields = fields


class VotoSerializer(serializers.ModelSerializer):
    candidato_nome_urna = serializers.CharField(source='candidato.nome_urna', read_only=True, allow_null=True)
    em_branco_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Voto
        fields = [
            'id', 'eleicao', 'candidato', 'candidato_nome_urna',
            'em_branco', 'em_branco_display', 'data_hora'
        ]
        read_only_fields = fields
    
    def get_em_branco_display(self, obj):
        return 'BRANCO' if obj.em_branco else None


class VotacaoInputSerializer(serializers.Serializer):
    eleitor_id = serializers.IntegerField()
    eleicao_id = serializers.IntegerField()
    candidato_id = serializers.IntegerField(required=False, allow_null=True)
    em_branco = serializers.BooleanField(required=False, default=False)
    
    def validate(self, data):
        eleitor_id = data.get('eleitor_id')
        eleicao_id = data.get('eleicao_id')
        candidato_id = data.get('candidato_id')
        em_branco = data.get('em_branco', False)
        
        try:
            eleicao = Eleicao.objects.get(id=eleicao_id)
        except Eleicao.DoesNotExist:
            raise serializers.ValidationError("Eleição não existe.")
        
        if eleicao.status != 'aberta':
            raise serializers.ValidationError("Eleição não está aberta para votação.")
        
        agora = timezone.now()
        if not (eleicao.data_inicio <= agora <= eleicao.data_fim):
            raise serializers.ValidationError("A votação não está dentro do período permitido.")
        
        try:
            eleitor = Eleitor.objects.get(id=eleitor_id)
        except Eleitor.DoesNotExist:
            raise serializers.ValidationError("Eleitor não existe.")
        
        if not AptidaoEleitor.objects.filter(eleitor_id=eleitor_id, eleicao_id=eleicao_id).exists():
            raise serializers.ValidationError("Eleitor não está apto a votar nesta eleição.")
        
        if RegistroVotacao.objects.filter(eleitor_id=eleitor_id, eleicao_id=eleicao_id).exists():
            raise serializers.ValidationError("Eleitor já votou nesta eleição.")        
        
        if em_branco:
            if candidato_id is not None:
                raise serializers.ValidationError("Não pode informar candidato e voto em branco simultaneamente.")
        else:
            if candidato_id is None:
                raise serializers.ValidationError("Deve informar candidato_id ou marcar em_branco como True.")
            
            try:
                candidato = Candidato.objects.get(id=candidato_id)
            except Candidato.DoesNotExist:
                raise serializers.ValidationError("Candidato não existe.")
            
            if candidato.eleicao_id != eleicao_id:
                raise serializers.ValidationError("Candidato não pertence a esta eleição.")
        
        return data
