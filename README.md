# Atlas - inventário de ativos, vulnerabilidades e risco

Interface web em Python/Flask sobre as classes do projeto original. O terminal
continua disponível com `python main.py`. A web usa o mesmo modelo de domínio,
JSON, cálculo CVSS e análise linear de risco; não é um protótipo com dados simulados.

## Comece por aqui

- [Revisão, evidências e atendimento aos requisitos](docs/AUDITORIA.md).
- [Instalação no servidor da disciplina e teste de 24 horas](docs/SERVIDOR.md).
- [Roteiro de testes da interface](docs/TESTE_MANUAL.md).
- [Explicação matemática e exemplos resolvidos](RISCO_EFETIVO.md).

## Executar no Fedora sem Docker

Python 3.11 ou superior. Se faltar pip: `sudo dnf install python3-pip`.
Na pasta deste projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python web.py
```

Abra **http://127.0.0.1:8000**. Crie uma conta ou entre com uma das contas locais
existentes. As credenciais de SSH da faculdade não são automaticamente contas da
aplicação. Não há senha padrão embutida.

`python web.py` serve para teste local. No servidor, use o Docker/Gunicorn abaixo.
A chave acima vale para esse terminal; trocar a chave encerra as sessões existentes.
`SECRET_KEY` precisa ter pelo menos 32 caracteres, e não deve entrar no Git.

Para testar com uma base isolada, antes de iniciar:

```bash
mkdir -p dados-teste
export INVENTARIO_ARQUIVO="$PWD/dados-teste/inventario.json"
export USUARIOS_ARQUIVO="$PWD/dados-teste/usuarios.json"
python web.py
```

Guarde essa pasta fora do Git. Para abrir o exemplo pronto de risco em uma base
isolada, copie `exemplos/risco_tres_ativos.json` para o caminho de inventário
**antes de iniciar**; não copie sobre uma base com dados que queira manter.

## Executar com Docker Compose

Requer Docker Engine e Compose v2 funcionando. No servidor compartilhado, o nome
do projeto deve ser único por aluno e a porta deve estar livre/autorizada:

```bash
python3 scripts/configurar.py --projeto inventario-sua-matricula --porta 18080
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
curl --fail http://127.0.0.1:18080/healthz
```

O script cria `.env` com chave aleatória e permissão 0600; não sobrescreve um
arquivo já existente. Substitua `sua-matricula` pelo identificador real em letras
minúsculas. No servidor, abra o navegador pelo túnel SSH explicado no guia.

A imagem usa Python 3.11, usuário sem privilégios, Gunicorn com **1 worker e 4
threads**, checagem de saúde e volume `/dados` para inventário **e contas**.
Os arquivos locais `usuarios.json`, `vulnerabilidades.json` e `.env` não entram na
imagem. Um volume novo começa sem contas e sem ativos. As instruções de migração
estão no guia do servidor.

Um worker é uma escolha explícita para o contexto acadêmico: o intervalo de
consultas NVD, o cache temporário de resultados e o limite de login vivem nesse
processo. Não aumente `--workers` sem externalizar esses estados. As operações de
inventário usam lock de arquivo e revisão para recusar formulários antigos.

**O requisito 3 só estará concluído depois da execução e verificação de pelo
menos 24 horas no servidor disponibilizado pelo docente.** Preparar os arquivos
Docker ou passar no CI não comprova esse tempo.

## Funcionalidades

| Tela | Operações |
| --- | --- |
| Visão geral | Indicadores reais, tratamentos pendentes e gráfico de risco próprio/herdado |
| Ativos | Criar, listar, buscar por ID/nome, filtrar tipo, editar, excluir e consultar detalhes |
| Vulnerabilidades | Criar, listar, filtrar, editar descrição/categoria/status/severidade/CVE/CVSS e excluir |
| Usuários | Cadastro, login, listagem, alteração do próprio login/senha e exclusão da própria conta |
| Consultar CVE | NVD 2.0, fontes/versões, importação escolhida, data e autoria; falhas de rede tratadas |
| Calcular CVSS | Questionário Base 3.1 ou vetor Base 3.0/3.1/4.0; cálculo e aplicação a um registro |
| Dependências | Criar/atualizar/listar/remover relações, com direção da transmissão e percentuais |
| Análise de risco | Risco próprio/herdado/efetivo, matrizes M/A/I−A, vetor v, equações e diagnóstico numérico |
| Exportar inventário | Download autenticado do array JSON de ativos, sem hashes de senha |

O desenho é responsivo, sem fontes, scripts ou gráficos de CDN. Apenas a consulta
NVD requer internet depois da instalação. A web não realiza varredura ou detecção
automática: associar um CVE exige conferir produtos, versões e condições afetadas.

## Contas, autoria e responsabilidade

- Todos os usuários autenticados são colaboradores do mesmo inventário. Não há
  administrador nem separação de ativos por dono. Cada pessoa só gerencia sua
  própria conta; a senha atual é exigida para alterações de conta.
- `responsavel` é a pessoa/equipe responsável operacionalmente. Opcionalmente,
  `responsavel_id` o vincula a uma conta selecionada na web.
- `adicionado_por` e `ultima_modificacao_por` são nomes históricos; os campos
  correspondentes terminados em `_id` identificam permanentemente as contas.
  Alterar o login mantém o ID e não reescreve o histórico. A tela de detalhes
  resolve o nome atual quando o ID ainda existe.
- Ao excluir uma conta, ativos/vulnerabilidades permanecem. Vínculos antigos
  retêm o ID e o nome histórico; uma nova conta com o mesmo login terá outro ID.
- Registros antigos sem IDs continuam legíveis. Não são associados automaticamente
  a uma conta só porque os nomes coincidem. Edite o responsável na web para
  estabelecer um vínculo explícito.
- Novas senhas usam scrypt com salt. Hashes SHA-256 da versão anterior são aceitos
  e migrados após um login válido. Logins antigos com espaços ou um caractere
  continuam funcionando; a regra de 2 a 64 caracteres vale para novos logins.
- Trocar a senha invalida sessões anteriores. Há CSRF nos formulários, escape de
  HTML, cookies HttpOnly/SameSite e limite de tentativas de login por IP.
- `PERMITIR_CADASTRO=false` fecha novos cadastros; as contas existentes continuam
  entrando. A configuração padrão preserva o cadastro disponível no programa original.

## Persistência e concorrência

O arquivo de ativos continua sendo **uma lista de objetos JSON**, um por ativo,
com vulnerabilidades e dependências aninhadas. `usuarios.json` é um arquivo
separado. `INVENTARIO_ARQUIVO` e `USUARIOS_ARQUIVO` permitem escolher os caminhos.

A escrita usa arquivo temporário, `fsync` e substituição atômica. A web recarrega
a base em cada operação e trava o ciclo ler/editar/salvar. Formulários incluem uma
revisão: se os dados mudarem em outra aba, uma resposta 409 pede para recarregar,
sem aplicar a edição antiga. Erros de JSON não são convertidos em base vazia.

Use a web como interface única da base em produção. Não execute o terminal,
edições manuais dos JSON ou restaurações de backup enquanto a web escreve na mesma
base. O CLI mantém uma coleção em memória; não é um cliente remoto multiusuário.

## Regras do risco e do CVSS

`b = Mv`, `x = b + Ax`, portanto `(I−A)x=b`. A linha i de A recebe risco da coluna j.
O cadastro exige Aii=0, pesos finitos em [0,1) e soma de linha <1. Dados importados
com soma >=1 são diagnosticados; isso sozinho não prova singularidade.

O cálculo verifica posto e número de condição antes de usar `numpy.linalg.solve`,
e confere o resíduo. O determinante é diagnóstico complementar. Sistema singular
ou numericamente inseguro não recebe uma solução apresentada como confiável.

A nota Base CVSS tem prioridade. Sem CVSS, usa-se a escala **local**, que não é
conversão oficial: NENHUMA=0, BAIXA=2, MEDIA=5, ALTA=8, CRITICA=10. Não avaliada
bloqueia o cálculo em vez de virar zero. Todos os registros entram, inclusive os
corrigidos, conforme a interpretação literal do modelo. O índice acumulado pode
exceder 10; não é probabilidade nem outra nota CVSS.

M tem uma coluna por ocorrência de vulnerabilidade cadastrada. O mesmo CVE em dois
ativos aparece como duas ocorrências, com severidade própria. A descrição completa
dessas escolhas está em `RISCO_EFETIVO.md`.

## Testes

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m flake8 . --count --select=E9,F63,F7,F82 --statistics
```

A suíte usa arquivos temporários e respostas NVD simuladas; o cálculo CVSS e a
álgebra linear são reais. O GitHub Actions roda em Python 3.11 e 3.12 em pushes de
qualquer branch e PRs. Um job separado constrói o container, testa HTTP e confirma
persistência após reinício. Esse job não executa a prova de 24 horas.

## Organização do código

| Arquivo | Responsabilidade |
| --- | --- |
| `equipamentos.py`, `modelos.py` | Classes, herança, composição, enumerações e validações |
| `inventario.py`, `dados.py`, `persistencia.py` | CRUD em memória, formato JSON e escrita atômica |
| `riscos.py` | Montagem das matrizes, invertibilidade, solução e diagnóstico |
| `seguranca.py`, `consulta_cve.py` | CVSS Base e consulta NVD |
| `autenticacao.py` | Contas, hash, migração, identidade e sessões |
| `servicos.py` | Unidade de trabalho web e controle de edições concorrentes |
| `web.py`, `templates/`, `static/` | Rotas, formulários, HTML, CSS e JavaScript |
| `main.py`, `menus.py`, `interface_cvss.py` | Interface de terminal preservada |
| `scripts/` | Configuração, smoke test de CI e monitor das 24 horas |

## Referências técnicas

- [Flask: Gunicorn](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/)
- [Flask: segurança](https://flask.palletsprojects.com/en/stable/web-security/)
- [Werkzeug: geração e verificação de hashes](https://werkzeug.palletsprojects.com/en/stable/utils/)
- [Docker Compose: serviços](https://docs.docker.com/reference/compose-file/services/)
- [Docker: publicação de portas](https://docs.docker.com/engine/network/port-publishing/)
