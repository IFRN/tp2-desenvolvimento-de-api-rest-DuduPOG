from django.db.models import Model, CharField, EmailField, CASCADE, PROTECT, DateField, BooleanField, DateTimeField, TextField, ForeignKey, PositiveIntegerField, URLField
from django.core.exceptions import ValidationError

# Create your models here.

class Eleitor(Model):
    nome = CharField(max_length=150)
    email = EmailField(unique=True)
    cpf = CharField(max_length=14, unique=True, help_text='000.000.000-00')
    data_nascimento = DateField()
    ativo = BooleanField(default=True)
    data_cadastro = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nome} ({self.cpf})"

    class Meta:
        ordering = ['nome']

class Eleicao(Model):
    tipos = [
        ('estudantil', 'Estudantil'),
        ('sindical', 'Sindical'),
        ('associacao', 'Associação'),
        ('condominio', 'Condomínio'),
        ('conselho', 'Conselho'),
        ('outra', 'Outra'),
    ]
    
    tipo_status = [
        ('rascunho', 'Rascunho'),
        ('aberta', 'Aberta'),
        ('encerrada', 'Encerrada'),
        ('apurada', 'Apurada'),
    ]

    titulo = CharField(max_length=200)
    descricao = TextField(blank=True)
    tipo = CharField(max_length=20, choices=tipos)
    data_inicio = DateTimeField()
    data_fim = DateTimeField()
    status = CharField(max_length=20, choices=tipo_status, default='rascunho')
    permite_branco = BooleanField(default=True)
    criada_por = ForeignKey(Eleitor, on_delete=PROTECT, related_name='eleicoes_criadas')

    def __str__(self):
        return f"{self.titulo} ({self.get_status_display()})"

    def clean(self):
        if self.data_fim <= self.data_inicio:
            raise ValidationError("Data de fim deve ser posterior à data de início.")

    class Meta:
        ordering = ['-data_inicio']


class Candidato(Model):
    eleicao = ForeignKey(Eleicao, on_delete=CASCADE, related_name='candidatos')
    numero = PositiveIntegerField()
    nome = CharField(max_length=150)
    nome_urna = CharField(max_length=50)
    partido_ou_chapa = CharField(max_length=100, blank=True)
    proposta = TextField(blank=True)
    foto_url = URLField(blank=True)

    def __str__(self):
        return f"{self.numero} - {self.nome_urna} ({self.eleicao.titulo})"

    class Meta:
        unique_together = [('eleicao', 'numero')]
        ordering = ['eleicao', 'numero']


class AptidaoEleitor(Model):
    eleitor = ForeignKey(Eleitor, on_delete=PROTECT, related_name='aptidoes')
    eleicao = ForeignKey(Eleicao, on_delete=CASCADE, related_name='aptos')
    data_inclusao = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.eleitor.nome} - {self.eleicao.titulo}"

    class Meta:
        unique_together = [('eleitor', 'eleicao')]
        ordering = ['eleicao', 'eleitor']


class RegistroVotacao(Model):
    eleitor = ForeignKey(Eleitor, on_delete=PROTECT, related_name='registros_votacao')
    eleicao = ForeignKey(Eleicao, on_delete=PROTECT, related_name='registros_votacao')
    data_hora = DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.eleitor.nome} votou em {self.eleicao.titulo}"

    class Meta:
        unique_together = [('eleitor', 'eleicao')]
        ordering = ['-data_hora']


class Voto(Model):
    eleicao = ForeignKey(Eleicao, on_delete=PROTECT, related_name='votos')
    candidato = ForeignKey(Candidato, on_delete=PROTECT, related_name='votos', null=True, blank=True)
    em_branco = BooleanField(default=False)
    data_hora = DateTimeField(auto_now_add=True)
    comprovante_hash = CharField(max_length=64, unique=True)

    def __str__(self):
        if self.em_branco:
            return f"Voto em branco - {self.eleicao.titulo}"
        return f"Voto em {self.candidato.nome_urna} - {self.eleicao.titulo}"

    def clean(self):
        if self.em_branco and self.candidato is not None:
            raise ValidationError("Voto em branco não pode ter candidato.")
        if not self.em_branco and self.candidato is None:
            raise ValidationError("Voto deve ter candidato ou ser em branco.")

    class Meta:
        ordering = ['-data_hora']
