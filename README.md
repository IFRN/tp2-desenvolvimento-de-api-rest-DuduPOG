[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/KEr3YAoF)
[![Open in Codespaces](https://classroom.github.com/assets/launch-codespace-2972f46106e565e64193e422d61a12cf1da4916b45550586e14ef0a7c637dd04.svg)](https://classroom.github.com/open-in-codespaces?assignment_repo_id=23907048)

# Guia de uso e instalação do projeto

## Descrição da estratégia de anonimato usada

Foi adotada uma separação física e lógica dos dados em duas entidades diferentes que não possuem relação direta via banco de dados, que são:

- Tabela RegistroVotacao: Esta tabela funciona como uma "folha de assinaturas". Ela registra quem votou e em qual eleição.
Possui uma restrição de unicidade (unique_together) entre eleitor e eleicao, garantindo que ninguém vote duas vezes.

- Tabela Voto (Urna Eletrônica): Registra o que foi votado (candidato ou voto em branco) e a qual eleição o voto pertence.

Um dos pontos mais relevantes é a ausência de chave estrangeira no voto, o que dificulta a relação entre o voto e quem votou,
também não existe registro de voto em nenhum log, por exemplo

Além disso, o QR Code ajuda o votante a saber em quem votou sem precisar se expor

## Criação do ambiente virtual

Na raiz do repositório, coloque o seguinte comando no terminal (o Python precisa estar instalado na sua máquina):

-**Windows:**

```bash
python -m venv (nome do ambiente virtual de preferência)
```

-**Linux:**

```bash
python3 -m venv (nome do ambiente virtual de preferência)
```

## Ativação do ambiente virtual

-**Windows:**

```bash
.\(nome do ambiente virtual de preferência)\Scripts\activate
```

-**Linux:**

```bash
source .(nome do ambiente virtual de preferência)/bin/activate
```

## Instalação de dependências

Ao ativar seu ambiente, instale as bibliotecas presentes no arquivo requirements.txt

-**Windows:**

```bash
pip install -r .\requirements.txt
```

-**Linux:**

```bash
pip install -r .\requirements.txt
```

## Execução do Projeto

Entre na raiz do projeto

-**Windows:**

```bash
cd .\eleicoes_api
```

-**Linux:**

```bash
cd eleicoes_api/
```

Antes de executar a aplicação Django, crie e faça as migrações do banco de dados,
para isso, certifique o seu pgAdmin está executando, crie um banco em um servidor
com o nome 'eleicoes_db' e após isso, execute os seguintes comandos:

-**Windows:**

```bash
python manage.py makemigrations
python manage.py migrate
```

-**Linux:**

```bash
python manage.py makemigrations
python manage.py migrate
```

Após garantir as migrações, execute o projeto:

-**Windows:**

```bash
python manage.py runserver
```

## Link do Swagger

```url
localhost:8000/swagger
ou
127.0.0.1:8000/swagger
ou
http://(domínio do codespace)/swagger/
```
