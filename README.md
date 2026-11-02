# Atlas — Gestão de ativos, vulnerabilidades e risco

Aplicação em Python para cadastrar ativos, acompanhar vulnerabilidades e analisar
como o risco se propaga entre equipamentos dependentes. Oferece interface web
responsiva e interface de terminal, persistência em JSON, consulta de CVEs na NVD,
cálculo de CVSS Base e análise de risco efetivo por álgebra linear.

Desenvolvido como projeto acadêmico, permite explorar o ciclo completo:
**cadastrar usuários e ativos → registrar vulnerabilidades → avaliar severidade →
definir dependências → visualizar o risco**.

## Funcionalidades

| Área | Recursos |
| --- | --- |
| Painel | Indicadores, tratamentos pendentes e gráfico de risco próprio e herdado |
| Ativos | Cadastro, listagem, busca, filtros, edição, exclusão e definição de responsável |
| Vulnerabilidades | Cadastro manual ou por CVE, edição, filtros e acompanhamento do tratamento |
| Usuários | Cadastro, autenticação, listagem e gerenciamento da própria conta |
| CVE | Consulta à NVD API 2.0 e seleção da avaliação associada ao registro |
| CVSS | Questionário Base 3.1 ou cálculo por vetor Base 3.0, 3.1 ou 4.0 |
| Dependências | Relações direcionais entre ativos, com pesos de transmissão de risco |
| Risco efetivo | Risco próprio, herdado e total; matrizes, equações e diagnóstico numérico |
| Exportação | Download autenticado do inventário em JSON, sem hashes de senha |

Depois de instalar as dependências, os cadastros, a calculadora e a análise de
risco funcionam sem internet. Apenas a consulta à NVD requer conexão.
A interface utiliza recursos locais, sem fontes, gráficos ou scripts de CDN.

## Instalação e execução local

Baixe e extraia o ZIP do repositório ou clone-o com Git. Abra um terminal **na
pasta que contém este README e o arquivo `requirements.txt`**.
No VS Code, use **Terminal → Novo Terminal**.

Requisitos: **Python 3.11 ou superior**, pip e navegador. O CI está configurado
para Python 3.11 e 3.12, que são as versões de referência.
A instalação inicial das dependências requer internet.

### Windows — PowerShell

Instale o Python pelo [site oficial](https://www.python.org/downloads/windows/).
No PowerShell, confira a versão e prepare o ambiente:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:SECRET_KEY = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
.\.venv\Scripts\python.exe -m app.web
```

Abra **http://127.0.0.1:8000** no navegador.

Os comandos usam diretamente o Python do ambiente virtual, dispensando a ativação
e mudanças na política de execução do PowerShell. Se `py` não estiver disponível,
mas `python --version` indicar uma versão compatível, substitua `py -3` por
`python` nos dois primeiros comandos.

Para iniciar novamente em outro terminal, execute as duas últimas linhas:
defina a chave e inicie a aplicação. Não é necessário reinstalar as dependências
a cada uso.

### Linux — Fedora, Ubuntu e Debian

Confira a versão com `python3 --version`. Se faltarem pip ou venv, instale os
pacotes correspondentes à distribuição.

Fedora:

```bash
sudo dnf install python3 python3-pip
```

Ubuntu/Debian:

```bash
sudo apt install python3 python3-pip python3-venv
```

Depois, na pasta do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -m app.web
```

Abra **http://127.0.0.1:8000**. Em outro terminal, ative novamente o ambiente,
defina a chave e execute `python -m app.web`.

### macOS

Com Python 3.11 ou superior instalado, use o mesmo bloco de criação do ambiente
virtual e execução apresentado para Linux. Os comandos `dnf` e `apt` são
exclusivos das distribuições Linux indicadas.

### Primeiro acesso e encerramento

1. Abra a aplicação e crie uma conta. Não há senha padrão embutida.
2. Cadastre um ativo e informe seu responsável; a web permite vinculá-lo a uma conta.
3. Registre uma vulnerabilidade manualmente ou consulte um CVE.
4. Avalie a severidade com CVSS e cadastre dependências, quando existirem.
5. Consulte o painel e a análise de risco.

Para encerrar o servidor local, pressione **Ctrl+C no terminal**.
O botão **Sair** da interface encerra apenas sua sessão de usuário.

A `SECRET_KEY` precisa ter pelo menos 32 caracteres aleatórios e permanecer
privada. Nos exemplos, vale para o terminal atual. Gerar outra chave invalida
sessões anteriores, mas preserva os dados. Para uma implantação permanente,
mantenha uma chave estável e protegida.

**A execução local não carrega o arquivo .env automaticamente.** Defina as
variáveis no terminal antes de iniciar. O comando `python -m app.web` usa o
servidor local do Flask, destinado a desenvolvimento e testes. Para implantação,
use o fluxo Docker abaixo. O Gunicorn não executa nativamente no Windows;
pode ser usado em Linux, WSL ou no container Linux.

## Interface de terminal

Após instalar as dependências, execute no Windows:

```powershell
.\.venv\Scripts\python.exe -m app.main
```

No Linux/macOS, com o ambiente virtual ativado:

```bash
python -m app.main
```

O terminal não exige `SECRET_KEY`. No menu principal, **6** abre vulnerabilidades,
**7** abre risco e dependências, **8** gerencia a própria conta e **9** encerra
o programa. No menu de vulnerabilidades, **6** consulta CVE, **7** calcula CVSS
e **8** volta.

## Executar com Docker Compose

Use Docker Engine com Compose v2 no Linux ou Docker Desktop com containers Linux
no Windows/macOS. O Docker precisa estar em execução. Para o script de
configuração, basta ter Python instalado; ele não exige as dependências do projeto.

Na pasta do projeto, gere a configuração uma única vez:

```bash
python3 scripts/configurar.py --projeto atlas-local --porta 18080
```

No PowerShell, use:

```powershell
py -3 scripts/configurar.py --projeto atlas-local --porta 18080
```

O script cria `.env` com chave aleatória e não sobrescreve um arquivo existente.
Mantenha esse arquivo privado. Em servidor compartilhado, escolha um nome de
projeto único e uma porta disponível e autorizada.

Os comandos seguintes são iguais nos dois sistemas:

```text
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

Abra **http://127.0.0.1:18080**.
O endpoint **http://127.0.0.1:18080/healthz** permite verificar a saúde do serviço.

| Ação | Comando |
| --- | --- |
| Acompanhar logs | `docker compose logs -f` |
| Parar | `docker compose stop` |
| Retomar | `docker compose start` |
| Reconstruir após atualizar o código | `docker compose up -d --build --wait --wait-timeout 180` |
| Remover containers, preservando o volume | `docker compose down` |

**Não use `docker compose down -v` se quiser preservar os dados:** a opção `-v`
remove o volume. Mantenha o nome do projeto para reutilizar o mesmo volume.

O container usa Gunicorn, usuário sem privilégios e volume persistente para
inventário e contas. Os JSON locais e o `.env` não são copiados para a imagem.
Um volume novo começa vazio. A porta é publicada apenas em `127.0.0.1`;
o acesso a um servidor remoto exige túnel SSH ou uma configuração de publicação
apropriada. Para exposição pública, configure HTTPS e a infraestrutura de acesso.

A configuração usa **1 worker e 4 threads**. O cache de consultas, o controle de
intervalo da NVD e o limite de tentativas de login mantêm estado no processo;
aumentar o número de workers exige adaptar esses controles.

Consulte o [guia de servidor e monitoramento](docs/SERVIDOR.md) para implantação,
migração, backup e coleta de evidências. A execução contínua de 24 horas exigida
no contexto acadêmico precisa ser demonstrada no servidor; o CI não substitui
essa verificação.

## Consulta de CVEs

CVE identifica uma vulnerabilidade conhecida. Na tela **Consultar CVE**, informe,
por exemplo, `CVE-2021-44228`, leia os resultados e confira se o produto, a versão
e as condições do ativo são afetados antes de cadastrá-la.

A consulta envia à NVD somente o identificador CVE, sem os dados do inventário.
Ela não realiza varredura nem confirma automaticamente que um ativo é vulnerável.
O status público do CVE é diferente do status de tratamento no inventário.

Quando há várias avaliações Base compatíveis, a aplicação permite escolher a
fonte e a versão. O cadastro preserva vetor, nota, versão, fonte e data da
consulta. Uma nova consulta não atualiza automaticamente registros existentes.

- Registros rejeitados não são importados.
- Sem avaliação compatível, o cadastro fica `NAO_AVALIADA`, com `cvss: null`.
- CVSS 2.0 e vetores com métricas além das Base não são suportados.
- O mesmo CVE pode afetar ativos diferentes; sua repetição no mesmo ativo é recusada.
- Falhas de rede, limites de uso e registros ausentes são apresentados ao usuário.

A chave `NVD_API_KEY` é opcional. Obtenha-a pelas orientações da
[NVD](https://nvd.nist.gov/developers/start-here), se necessário, e configure-a no
ambiente ou no `.env` do Compose. Ela é enviada em cabeçalho e não é salva no JSON.
Não publique a chave. Em caso de limite de uso, aguarde antes de consultar
novamente; os demais recursos continuam disponíveis.

## Cálculo de CVSS

CVSS expressa a severidade técnica da vulnerabilidade. A calculadora oferece
questionário **Base 3.1** e aceita vetores **Base 3.0, 3.1 e 4.0**. O cálculo usa
a biblioteca `cvss` e não depende da NVD.

Exemplo didático:

```text
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
```

Resultado esperado: **9,8 — CRÍTICA**. O vetor não identifica, por si só, um CVE.

| Métrica Base 3.1 | Significado |
| --- | --- |
| AV | Vetor de ataque |
| AC | Complexidade do ataque |
| PR | Privilégios necessários |
| UI | Interação do usuário |
| S | Escopo: impacto além da autoridade de segurança do componente |
| C | Impacto na confidencialidade |
| I | Impacto na integridade |
| A | Impacto na disponibilidade |

Escolha as métricas com base na análise técnica da falha. É possível consultar
o resultado ou aplicá-lo a uma vulnerabilidade cadastrada, atualizando sua
severidade. A avaliação local registra a fonte **Cálculo local**. Informar um
CVE nesse fluxo valida sua sintaxe, sem confirmar sua existência online.

| Nota Base | Classificação |
| --- | --- |
| 0,0 | NENHUMA |
| 0,1–3,9 | BAIXA |
| 4,0–6,9 | MÉDIA |
| 7,0–8,9 | ALTA |
| 9,0–10,0 | CRÍTICA |

A calculadora aceita somente métricas Base: vetores com métricas temporais,
ambientais, de ameaça ou suplementares são recusados. A prioridade de correção
também depende da exposição e do contexto do ativo; a nota isolada não substitui
essa avaliação.

## Risco efetivo e dependências

O modelo soma o risco próprio e o risco recebido de outros ativos:

```text
b = Mv
x = b + Ax
(I − A)x = b
```

| Símbolo | Interpretação |
| --- | --- |
| M | Matriz de incidência: relaciona ativos às ocorrências de vulnerabilidade |
| v | Vetor de severidades |
| b | Risco próprio de cada ativo |
| A | Matriz de dependências: A[i,j] transmite risco do ativo j para o ativo i |
| x | Risco efetivo; o risco herdado é x − b |

A nota Base CVSS tem prioridade. Sem ela, usa-se a escala **local**
NENHUMA=0, BAIXA=2, MEDIA=5, ALTA=8 e CRITICA=10, que não é uma conversão oficial
do CVSS. Uma vulnerabilidade não avaliada bloqueia o cálculo em vez de virar zero.

O cadastro exige pesos finitos entre 0 e 1, sem incluir 1, sem autodependência
e com soma dos pesos recebidos menor que 1. O cálculo verifica posto e
condicionamento antes de resolver o sistema com `numpy.linalg.solve`, além de
conferir o resíduo. Sistemas singulares ou numericamente inseguros recebem
diagnóstico.

**O risco efetivo pode superar 10:** é um índice acumulado, não uma nota CVSS
nem uma probabilidade. No modelo implementado, todas as vulnerabilidades
cadastradas entram no cálculo, inclusive as marcadas como corrigidas.

Veja a [explicação matemática e exemplos resolvidos](docs/RISCO_EFETIVO.md).
A pasta `exemplos/` contém bases para explorar o modelo.

## Contas, dados e configuração

Todos os usuários autenticados colaboram no mesmo inventário. Não há perfis de
administrador nem separação de ativos por proprietário. Cada pessoa gerencia
apenas a própria conta; alterações exigem a senha atual.

Responsabilidade operacional e autoria são informações distintas. O responsável
pode ser vinculado a uma conta, enquanto os registros de criação e alteração
preservam o histórico. Renomear ou excluir uma conta não exclui ativos e
vulnerabilidades; os identificadores estáveis evitam atribuir o histórico a
outra pessoa que reutilize o mesmo login.

Novas senhas usam scrypt com salt. Hashes legados SHA-256 são migrados após login
válido. A troca de senha invalida sessões anteriores. A interface inclui proteção
CSRF, escape de HTML, cookies HttpOnly/SameSite e limite de tentativas de login.

### Variáveis de ambiente

| Variável | Uso |
| --- | --- |
| `SECRET_KEY` | Chave privada obrigatória para sessões web, com pelo menos 32 caracteres |
| `INVENTARIO_ARQUIVO` | Caminho alternativo para o JSON de ativos |
| `USUARIOS_ARQUIVO` | Caminho alternativo para o JSON de contas |
| `NVD_API_KEY` | Chave opcional para consultas à NVD |
| `PERMITIR_CADASTRO` | `true` por padrão; `false` fecha novos cadastros |
| `COOKIE_SEGURO` | `false` para HTTP local; use `true` quando o acesso ocorrer por HTTPS |
| `COMPOSE_PROJECT_NAME` | Nome do projeto Compose e prefixo de seus recursos |
| `PORTA_WEB` | Porta publicada pelo Compose; padrão 18080, sem efeito no servidor local |

No Windows, defina variáveis com `$env:NOME = "valor"`; em Linux/macOS, com
`export NOME="valor"`. Para o Compose, edite o `.env` e execute novamente
`docker compose up -d` para aplicar mudanças.

### Persistência, backup e atualização

Por padrão, os arquivos são `dados/vulnerabilidades.json` e
`dados/usuarios.json`. O inventário é uma lista JSON de ativos com suas
vulnerabilidades e dependências. As contas ficam em arquivo separado.

Por compatibilidade, JSON antigos que ainda existam na raiz têm prioridade sobre
os arquivos de `dados/`. As variáveis de ambiente têm prioridade sobre ambos.
Ao migrar uma instalação, pare a aplicação, faça backup dos dois JSON, mova-os
para `dados/` e retire as cópias antigas da raiz após conferir os dados.

A escrita é atômica. Na web, travas e revisão de formulários protegem contra
edições concorrentes; uma resposta **409** solicita recarregar dados alterados
por outra operação. JSON inválido gera erro e não é substituído por base vazia.

Não use o terminal e a web simultaneamente para editar a mesma base.
Faça backups e restaurações com a aplicação parada. A exportação pela interface
contém o inventário; ela não substitui o backup das contas.

Para experimentar sem alterar a base principal, configure caminhos diferentes
com `INVENTARIO_ARQUIVO` e `USUARIOS_ARQUIVO`. Também é possível copiar um arquivo
de `exemplos/` para o inventário de teste, antes de iniciar a aplicação.

Os JSON de usuários e inventário, ambientes virtuais e segredos estão no
`.gitignore`. Não publique dados reais nem credenciais; arquivos já rastreados
pelo Git não deixam de ser rastreados apenas por entrarem nesse arquivo.

## Testes automatizados

No Linux/macOS, com o ambiente virtual ativado:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m flake8 app tests scripts --count --select=E9,F63,F7,F82 --statistics
```

No Windows — PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flake8 app tests scripts --count --select=E9,F63,F7,F82 --statistics
```

Os testes usam bases temporárias e respostas NVD simuladas; os cálculos de CVSS e
álgebra linear são reais. Cobrem CRUD, contas, persistência, menus, rotas web,
tratamento de erros e análise de risco.

O GitHub Actions está configurado para testar Python 3.11 e 3.12 em pushes e
pull requests. Um job separado constrói o container, testa HTTP e verifica a
persistência após reinício. Consulte a aba **Actions** para o resultado da versão
que estiver utilizando.

## Organização do projeto

| Caminho | Conteúdo |
| --- | --- |
| `app/` | Domínio, persistência, serviços e interfaces web/terminal |
| `app/templates/` e `app/static/` | HTML, CSS, JavaScript e ícones |
| `tests/` | Testes automatizados |
| `docs/` | Guias de uso, implantação, auditoria e modelo matemático |
| `scripts/` | Configuração, teste HTTP e monitoramento |
| `exemplos/` | Inventários demonstrativos de risco |
| `dados/` | Dados locais, fora do versionamento |
| `Dockerfile` e `compose.yaml` | Construção e execução do serviço |
| `requirements*.txt` | Dependências de execução e desenvolvimento |

Os módulos `equipamentos.py` e `modelos.py` representam o domínio;
`inventario.py`, `dados.py` e `persistencia.py` cuidam do inventário;
`seguranca.py`, `consulta_cve.py` e `riscos.py` concentram as avaliações.
`web.py` e `servicos.py` atendem a interface web, enquanto `main.py` e
`menus.py` atendem o terminal. Todos ficam em `app/`.

## Problemas frequentes

| Problema | Como resolver |
| --- | --- |
| `No module named pip` no Fedora | Instale `python3-pip`, crie o ambiente virtual e use seu Python para instalar dependências |
| `py` não reconhecido no Windows | Confira a instalação; use `python` se apontar para uma versão compatível |
| Ativação bloqueada no PowerShell | Use diretamente `.\.venv\Scripts\python.exe`, conforme as instruções |
| `No module named app` | Execute da pasta que contém `app/`, usando `-m app.web` ou `-m app.main` |
| Erro de `SECRET_KEY` | Defina a variável no mesmo terminal; o modo local não lê `.env` |
| Porta em uso no Docker | Escolha outra `PORTA_WEB` no `.env` e aplique com `docker compose up -d` |
| Consulta NVD falha | Confira conexão e identificador; em caso de limite, aguarde |
| Formulário retorna 409 | Recarregue a página e confira os dados atuais antes de reenviar |
| Erro de leitura do JSON | Preserve o arquivo, pare a aplicação e confira o conteúdo ou restaure um backup |
| Dados não aparecem após atualização | Confira os caminhos configurados, JSON antigos na raiz e o volume Compose |

## Documentação complementar

- [Roteiro de testes manuais da interface](docs/TESTE_MANUAL.md).
- [Modelo de risco e exemplos resolvidos](docs/RISCO_EFETIVO.md).
- [Implantação, backup e monitoramento no servidor](docs/SERVIDOR.md).
- [Auditoria e evidências da revisão](docs/AUDITORIA.md).

## Referências

- [CVE — identificação de vulnerabilidades](https://www.cve.org/).
- [NVD — API de vulnerabilidades](https://nvd.nist.gov/developers/vulnerabilities).
- [FIRST — especificação CVSS 3.1](https://www.first.org/cvss/v3.1/specification-document).
- [FIRST — especificação CVSS 4.0](https://www.first.org/cvss/v4.0/specification-document).
- [Biblioteca Python cvss](https://pypi.org/project/cvss/3.6/).
- [NumPy — solução de sistemas lineares](https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html).
- [Python — ambientes virtuais](https://docs.python.org/3/library/venv.html).
- [Flask — implantação com Gunicorn](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/).
- [Docker Compose — referência](https://docs.docker.com/reference/compose-file/).

