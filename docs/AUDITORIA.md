# Revisão técnica — OrthoCRUD 1.0.1

Revisão realizada em **04/11/2026**, a partir do código da release 1.0.0.
Este documento registra verificações desta revisão; não certifica aprovação
acadêmica nem o estado atual de uma instalação remota.

## Correções verificadas

| Problema | Correção e verificação |
| --- | --- |
| Trocar ou remover o CVE, mantendo o vetor CVSS, preservava a fonte do CVE anterior | A fonte passa a “Cálculo local” e a data de consulta é removida. Dois testes reproduziram a falha antes da correção. |
| O monitor podia encerrar com JSON que não fosse um objeto ou com resposta HTTP interrompida | Validação da resposta e registro da falha permitem continuar a coleta sem aprovar o período com erro. Três casos reproduziram a falha; outro confirma rejeição de uptime booleano. |
| Um teste dependia do diretório de onde o pytest era chamado | O caminho do exemplo singular passa a ser relativo ao arquivo de teste. |
| CI e README descreviam validações diferentes | Workflow atualizado para Python 3.11/3.12, pushes em branches e job de container com teste HTTP e persistência. |
| A release não continha .dockerignore nem .env.example | Arquivos incluídos; contexto de build limitado ao necessário, exemplo sem segredo e porta configurável. |
| Guia público continha identificação pessoal e endereço da instituição | Substituídos por marcadores; incluído o atalho SSH e esclarecidas as portas. |

## Resultados desta revisão

- **220 testes e 10 subtestes aprovados**, executados em Linux com Python 3.12.14.
- **Zero erros** no lint crítico E9/F63/F7/F82.
- Teste HTTP real com servidor Werkzeug: cadastro, login, criação e exportação
  de ativo e saúde da aplicação.
- A aplicação foi encerrada e criada novamente com os mesmos arquivos temporários;
  nova autenticação e exportação confirmaram persistência.
- Conferência de links locais, sintaxe dos comandos Bash documentados e conteúdo
  do ZIP: sem caches, ambientes virtuais, contas reais ou segredos.
- Consultas NVD simuladas nos testes; os cálculos de CVSS e álgebra linear são reais.

## Limites da verificação

Docker Engine não estava disponível neste ambiente. O build e a execução do
container devem ser confirmados pelo job de CI e pela implantação.
Não foram executados testes em Windows/macOS, nem uma nova inspeção visual
em navegador nesta revisão.

Não houve acesso ao servidor da instituição nem análise de evidências reais
de 24 horas. Simulações de tempo nos testes verificam o monitor, mas não comprovam
execução contínua de uma implantação. A cobertura de código não foi recalculada.

## Decisões do projeto

- O inventário é compartilhado entre usuários autenticados; cada pessoa gerencia
  a própria conta. Não há papéis administrativos nem isolamento por proprietário.
- Autoria guarda criador e último editor; não constitui um histórico imutável
  de todas as operações.
- CVSS mede severidade técnica. O risco efetivo é um índice acumulado que pode
  superar 10. Vulnerabilidades sem avaliação impedem o cálculo.
- O modelo inclui todos os registros, inclusive os marcados como corrigidos,
  e usa uma coluna de M por ocorrência de vulnerabilidade.
- Dados ficam em JSON, com escrita atômica, trava e revisão na web. Não execute
  CLI e web editando a mesma base ao mesmo tempo.
- Gunicorn permanece com um worker: cache NVD e limite de login são locais ao
  processo. Múltiplos workers exigem rever esses estados compartilhados.

Consulte [o modelo matemático](RISCO_EFETIVO.md),
[o roteiro manual](TESTE_MANUAL.md) e [o guia do servidor](SERVIDOR.md).
O histórico da atualização está no [CHANGELOG](../CHANGELOG.md).

