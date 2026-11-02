# Sistema de gerenciamento de ativos e vulnerabilidades

Aplicação de terminal em Python com persistência JSON, consulta de CVEs na NVD
(API 2.0), cálculo **CVSS Base** e **risco efetivo por álgebra linear** (requisito 4). Mantém as funcionalidades anteriores de
cadastro, busca, atualização e remoção de ativos e vulnerabilidades.

## Novidade: risco efetivo

No menu principal, escolha **7 — Análise de risco e dependências**:

1. Cadastre ou altere dependências (quem recebe o risco, origem e peso).
2. Liste as relações cadastradas.
3. Remova uma relação.
4. Consulte o risco próprio, herdado e efetivo de todos os equipamentos.
5. Exiba as matrizes M, v, A, I − A e o diagnóstico numérico.
6. Volte ao menu principal.

O menu de vulnerabilidades mantém **6 = consultar CVE**, **7 = calcular CVSS**
e **8 = voltar**. No principal, **7 = análise de risco** e **8 = sair** (última opção).

Veja [RISCO_EFETIVO.md](RISCO_EFETIVO.md) para o modelo matemático, escolhas de
implementação, exemplo resolvido à mão e roteiro de apresentação.

## Instalação e execução

Requer Python 3.11 ou superior. No Fedora, se necessário, instale o pip com
`sudo dnf install python3-pip`. Na pasta do projeto, prepare o ambiente:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale também as dependências atualizadas (esta versão acrescenta NumPy):

```bash
python -m pip install -r requirements.txt
python main.py
```

Recomenda-se instalar em um ambiente virtual (`python -m venv .venv`).
Ativação no Windows: `.venv\Scripts\activate`; Linux/macOS: `source .venv/bin/activate`.

A instalação das dependências precisa de internet. Depois de instaladas,
o cadastro, a leitura dos dados, a calculadora e a análise de risco funcionam sem conexão.
Apenas a consulta à NVD requer acesso à internet.

## Consultar e cadastrar um CVE

1. Cadastre o ativo, se necessário.
2. No menu principal, escolha **6 — Gerenciar vulnerabilidades**.
3. Escolha **6 — Consultar CVE na NVD e cadastrar**.
4. Digite um identificador, por exemplo `CVE-2021-44228`.
5. Leia a descrição, o status público do registro, as avaliações e o link da NVD.
6. Confira se o produto, a versão e as condições do seu ativo são afetados.
7. Confirme o cadastro, selecione o ativo e, se houver várias avaliações,
   escolha a fonte/versão desejada. Informe categoria e status do tratamento.

A consulta não faz varredura, não detecta automaticamente softwares e não
confirma que o ativo está vulnerável. Envia somente o CVE à NVD, nunca os dados
do inventário. O status público do CVE é diferente do status de tratamento local.

O sistema exibe todas as avaliações Base compatíveis encontradas, na ordem
4.0, 3.1 e 3.0. Não combina notas nem escolhe automaticamente a maior nota.
Cada avaliação mantém o vetor, a versão e a fonte informada pela NVD, que pode
ser o NIST ou outra organização. O JSON armazena a avaliação escolhida.
Uma nova consulta não atualiza registros antigos automaticamente.

Registros rejeitados não são importados. Sem nota compatível, o cadastro fica
**NAO_AVALIADA**, com `cvss: null`, em vez de receber nota zero.
Notas divergentes do cálculo do vetor são ignoradas com aviso. Vetores contendo
métricas além das Base não são importados nesta versão. CVSS 2.0 não é suportado.

## Calcular CVSS localmente

Em **Gerenciar vulnerabilidades**, escolha **7 — Calcular CVSS e aplicar a uma
vulnerabilidade**. Há duas formas:

- **Questionário CVSS 3.1:** responda às oito métricas Base. As respostas geram
  um vetor e a biblioteca `cvss==3.6` executa o cálculo padronizado.
- **Colar vetor:** aceita vetores Base de CVSS 3.0, 3.1 e 4.0.

Exemplo didático (não representa, por si só, um CVE específico):

```text
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
```

Resultado esperado: **9.8 — CRITICA**. No questionário, escolha respectivamente
`1, 1, 1, 1, 1, 3, 3, 3` para obter o mesmo vetor.

| Métrica 3.1 | Significado |
| --- | --- |
| AV | Vetor de ataque: rede, adjacente, local ou físico |
| AC | Complexidade e condições fora do controle do atacante |
| PR | Privilégios necessários antes da exploração |
| UI | Necessidade de interação de outra pessoa |
| S | Se o impacto ultrapassa a autoridade de segurança do componente |
| C | Impacto na confidencialidade |
| I | Impacto na integridade |
| A | Impacto na disponibilidade |

A seleção das métricas exige análise técnica da falha. A ferramenta calcula a
nota das respostas; ela não descobre as respostas sozinha. Consulte a
especificação para os critérios completos, especialmente a métrica de escopo.

É possível apenas visualizar o resultado ou aplicá-lo a uma vulnerabilidade já
cadastrada. Para uma falha nova sem CVE, use primeiro o cadastro manual (opção 1).
Ao aplicar uma avaliação, a severidade é atualizada automaticamente. Substituir
uma avaliação existente exige confirmação e passa a registrar a fonte como
**Cálculo local**. A data de consulta, quando presente, continua se referindo à
consulta do CVE, não ao novo cálculo local.

O CVE pode ser informado opcionalmente nesse fluxo. Sua sintaxe é validada,
mas sua existência não é verificada online. Não é permitido repetir o mesmo CVE
no mesmo ativo por estes fluxos; o mesmo CVE pode afetar ativos diferentes.

### Escopo da calculadora

Esta entrega calcula **apenas a pontuação Base**, sem métricas temporais,
ambientais, de ameaça ou suplementares. Vetores com essas métricas são
recusados explicitamente, sem descartá-las silenciosamente.

| Nota | Classificação |
| --- | --- |
| 0.0 | NENHUMA |
| 0.1–3.9 | BAIXA |
| 4.0–6.9 | MEDIA |
| 7.0–8.9 | ALTA |
| 9.0–10.0 | CRITICA |
| Sem avaliação | NAO_AVALIADA (ou severidade manual preexistente) |

CVSS mede severidade técnica. A prioridade de correção também depende da
exposição, importância do ativo e contexto de exploração. Notas de versões
CVSS diferentes não devem ser tratadas como equivalentes.

## Rede e chave da NVD

A consulta usa HTTPS e timeout de 15 segundos. Falhas de conexão, respostas
inválidas, erros HTTP, limites de uso e CVEs ausentes geram mensagens no terminal.
As demais funções continuam disponíveis. Sem chave, o cliente espera pelo menos
6 segundos entre suas requisições; com chave, 0,6 segundo. Esse controle é por
instância do cliente, não global entre computadores/processos. Não há retries
automáticos nem cache de consultas.

Uma chave é opcional e pode ser fornecida pela variável de ambiente
`NVD_API_KEY`. Ela é enviada em cabeçalho e não é salva no JSON. Não coloque
chaves no código ou no repositório. Em caso de bloqueio ou limite, aguarde antes
de tentar novamente; os limites e condições do serviço podem mudar.

## Dados e compatibilidade

O arquivo padrão continua sendo `vulnerabilidades.json`, ao lado de `main.py`.
É possível definir outro caminho com `INVENTARIO_ARQUIVO`. Faça backup de sua
base antes de substituir uma instalação anterior.

Os registros antigos continuam sendo lidos. Campos novos são opcionais:

```json
{
  "descricao": "Exemplo didático de falha",
  "categoria": "Software",
  "severidade": "CRITICA",
  "status": "ABERTA",
  "cve_id": null,
  "cvss": {
    "versao": "3.1",
    "vetor": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "nota": 9.8,
    "fonte": "Cálculo local"
  },
  "consultado_em": null
}
```

Esse objeto fica dentro da lista de vulnerabilidades de um ativo; não substitui
o formato geral do inventário. Na leitura, versão e nota são conferidas contra
o vetor. As opções antigas do menu conservaram sua numeração.

## Organização do código

| Arquivo | Responsabilidade |
| --- | --- |
| `seguranca.py` | Validação de CVE, cálculo e classificação CVSS, serialização da avaliação |
| `consulta_cve.py` | HTTP, intervalo de requisições, interpretação da resposta NVD |
| `interface_cvss.py` | Questionário 3.1, entrada de vetor e exibição da avaliação |
| `modelos.py` | Vulnerabilidade, associação ao CVE e severidade derivada da avaliação |
| `menus.py` | Consulta, escolha da avaliação, cadastro e aplicação do cálculo |
| `test_cve_cvss.py` | Testes da integração, cálculo, persistência e falhas |
| `equipamentos.py` | Hierarquia de ativos e objetos Dependencia |
| `riscos.py` | Montagem de M, v e A; diagnóstico e solução do sistema linear |
| `test_riscos.py` | Casos manuais, estabilidade, dependências, persistência e menus |

O cálculo matemático é delegado à biblioteca `cvss`, evitando implementar
manualmente as fórmulas, arredondamentos e tabelas de CVSS 4.0.

## Testes

```bash
python -m pytest -q
python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

Os testes automáticos simulam a rede, usando cálculos reais. Cobrem vetores de
referência, faixas, entradas inválidas, múltiplas fontes, notas ausentes ou
divergentes, CVEs rejeitados, timeout, HTTP 403/429/500, leitura de dados antigos,
recarga do JSON e fluxos do menu. Não dependem da disponibilidade da NVD.

## Docker

O `Dockerfile` instala todas as dependências declaradas, inclusive NumPy. O
`compose.yaml` mantém a entrada interativa aberta e os dados em um volume.

```bash
docker compose up -d --build
docker compose attach inventario
```

Se o menu não reaparecer ao conectar, pressione Enter. Para se desconectar e
manter o programa em execução, use **Ctrl+P e depois Ctrl+Q**, sem escolher Sair.
Para parar o serviço, use `docker compose down`. O volume é preservado.
Com `restart: unless-stopped`, sair pelo menu pode reiniciar o serviço; use
`docker compose down` quando a intenção for encerrá-lo.

A base do container começa vazia e é independente do JSON local. Para usar uma
base existente, com o serviço parado (antes do primeiro `up`, ou após `stop`):

```bash
docker compose run --rm -T inventario python -c "from pathlib import Path; import sys; Path('/dados/vulnerabilidades.json').write_bytes(sys.stdin.buffer.read())" < vulnerabilidades.json
docker compose up -d
```

Esse comando substitui a base do volume. Use-o somente na inicialização ou
após fazer backup da base anterior. Não execute duas instâncias do programa
escrevendo simultaneamente no mesmo JSON.

Verifique o tempo contínuo de execução com `docker compose ps` e:

```bash
docker inspect --format '{{.State.StartedAt}} | reinícios={{.RestartCount}}' "$(docker compose ps -q inventario)"
```

O requisito de **24 horas** precisa ser demonstrado no servidor do docente.
Os arquivos Docker estão preparados, mas esta entrega não comprova esse período.
Docker não estava disponível no ambiente de edição; a construção da imagem e
os testes dentro dela estão configurados no CI e devem ser confirmados no GitHub.

O workflow executa os testes em pushes de qualquer branch e em pull requests
para main. Isso permite validar esta versão antes de fazer merge.

## Referências

- NVD API: https://nvd.nist.gov/developers/vulnerabilities
- Recomendações de uso: https://nvd.nist.gov/developers/start-here
- CVSS 3.1: https://www.first.org/cvss/v3.1/specification-document
- CVSS 4.0: https://www.first.org/cvss/v4.0/specification-document
- Biblioteca e exemplos: https://pypi.org/project/cvss/3.6/
- Identificadores CVE: https://www.cve.org/

- NumPy solve: https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html
- NumPy matrix_rank: https://numpy.org/doc/stable/reference/generated/numpy.linalg.matrix_rank.html
- NumPy cond: https://numpy.org/doc/stable/reference/generated/numpy.linalg.cond.html
