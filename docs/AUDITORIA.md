# Revisão técnica e atendimento aos requisitos

Data: 02/11/2026. Base examinada: `trabalho2-main.zip`, `Trabalho_2(1).pdf` e
imagem de instruções SSH enviados nesta solicitação. A revisão usa a versão
atualizada com usuários, não o projeto anterior desta conversa.

## Resultado

A aplicação atende tecnicamente aos requisitos **1, 2 e 4** descritos no PDF,
com as ressalvas de modelagem abaixo. A interface web foi implementada sobre o
mesmo domínio. O requisito **3 permanece pendente de execução e comprovação no
servidor por pelo menos 24 horas**. Não atribuo nota nem declaro aprovação do docente.

O PDF informa que os requisitos do trabalho anterior permanecem válidos, mas esse
enunciado anterior não veio nos anexos. Portanto, não é possível certificar aqui
requisitos que só apareçam nele.

| Requisito do Trabalho 2 | Peso | Avaliação e evidência |
| --- | ---: | --- |
| 1. Ativos como objetos individuais | 20% | Atendido no código: Equipamento abstrato, cinco subclasses por tipo, fábrica e composição de vulnerabilidades/dependências. Os testes verificam instanciação, polimorfismo e preservação na troca de tipo. |
| 2. Ativos persistidos como array JSON | 20% | Atendido: um objeto por ativo em uma lista; relações aninhadas. Testes de ida/volta, JSON legado/inválido, duplicidade de ID, referência inexistente e escrita atômica. Arquivo de contas separado não altera o formato dos ativos. |
| 3. Container por pelo menos 24 horas | 45% | Preparado, ainda não comprovado: Dockerfile/Compose com servidor web persistente, volume, healthcheck e reinício. Incluídos CI de container e coleta de evidências para execução pelo aluno. |
| 4. Risco efetivo por modelo linear | 15% | Atendido no código/testes: monta M/v/A, calcula b=Mv, verifica posto/condição, resolve (I−A)x=b e apresenta próprio/efetivo. Casos manual, cíclico, singular e mal condicionado testados. |

Esses pesos descrevem a tabela do PDF, não constituem previsão da nota final.

## Testes executados e limites

- **Versão recebida:** 126 testes e 10 subtestes aprovados; lint de erros críticos
  aprovado. Isso não cobria o CRUD de usuários.
- Foram escritos cinco testes de regressão antes das correções. Os cinco
  falharam na versão recebida e passaram após a correção.
- **Versão final:** 211 testes e 10 subtestes aprovados, em Python 3.12.14, Linux.
  A execução com cobertura levou 13,76 s neste ambiente. `pip check` não encontrou
  dependências quebradas; lint E9/F63/F7/F82 apresentou zero erros.
- Cobertura de linhas dos módulos selecionados: **88% no agregado**, incluindo
  scripts. `app/web.py`: 95%; `app/autenticacao.py`: 90%; `app/riscos.py`: 93%; `app/dados.py`: 98%.
  Não é cobertura total do repositório nem garantia de ausência de falhas. Menus
  são exercitados pelos testes originais, mas não incluídos nesse agregado.
- Navegador Chromium real: login, sete telas em desktop (1440 × 1000), quatro
  telas em celular (390 × 844), cadastro/exclusão de ativo, vulnerabilidade,
  cálculo/aplicação de CVSS. Sem erros JavaScript nem overflow horizontal da página;
  tabelas largas têm rolagem interna. Inspeção visual realizada.
- HTTP real com Gunicorn: conta, login, cadastro e exportação de ativo; reinício
  do processo e nova autenticação, confirmando persistência. Monitor real curto:
  5 amostras em cerca de 7,2 segundos, sem falhas, marcando corretamente que **não**
  é evidência de 24 horas.
- Não havia Docker Engine/daemon disponível no ambiente desta revisão. O build e
  a execução real do container não foram realizados aqui. A estrutura foi revisada
  e o CI foi preparado para executar esses passos no GitHub; ainda deve ser observado
  na sua branch. Python 3.11 está configurado no CI e na imagem, não foi a versão
  local de execução da suíte.
- O servidor privado 10.0.99.150 não foi acessado. O teste de 24 horas não foi
  executado. O acesso SSH depende de sua matrícula e da rede/VPN da instituição.
- A NVD foi simulada nos testes automatizados para torná-los reproduzíveis. Foram
  testados retornos válidos, versões/fontes, sem nota, rejeitado, divergência,
  timeout e limitação de acesso. Isso não comprova a conectividade atual do servidor
  com a NVD; o guia inclui o teste manual online.

O arquivo de ativos recebido estava vazio. As três contas existentes foram
preservadas, e a leitura foi verificada sem revelar hashes ou modificar suas
senhas. Os cenários de risco usam os exemplos e bases temporárias, não dados reais.

## Problemas encontrados e tratamento

| Achado na versão recebida | Impacto | Alteração |
| --- | --- | --- |
| SHA-256 direto sem salt | Senhas iguais tinham hashes iguais e derivação inadequada para senhas | scrypt com salt; migração após login válido; sem reset forçado das contas existentes |
| Validação de senha só na criação pelo menu | Funções aceitavam senha curta e mudança sem mesma política | Validação no módulo de contas e confirmação/senha atual na interface |
| Troca de senha de usuário inexistente criava conta | Criação acidental fora do cadastro | Operação rejeitada com erro e sem gravação |
| Renomear usuário inexistente gerava KeyError | Fluxo interrompido | Resultado controlado, com testes |
| CVE importado sem autor | Perda de rastreabilidade | Criador/último editor e IDs registrados |
| Contas em caminho relativo e fora do volume | Dependência do diretório atual e perda ao recriar container | Caminho configurável e contas/inventário no volume /dados |
| Conta gravada diretamente no arquivo | Possibilidade de JSON parcial em falha | Escrita temporária com fsync e substituição atômica |
| JSON inválido iniciava com inventário vazio | Gravação posterior podia apagar a base original | Inicialização bloqueada; arquivo preservado e cópia de segurança no CLI |
| Relação com usuário só por texto | Renomeação reescrevia histórico e confundia identidade | IDs permanentes e vínculo explícito de responsável; nomes históricos preservados |
| Ausência de controle de edição concorrente | Abas/usuários podiam sobrescrever mudanças | Lock no ciclo de escrita e revisão dos formulários; conflito HTTP 409 |
| Container executava menu interativo | Dependência de stdin/TTY, pouco adequado a serviço contínuo | Gunicorn persistente, sem terminal, healthcheck e logs |
| CI disparava apenas nas branches configuradas para main | Push isolado em branch podia não executar teste | Push e PR em qualquer branch; job de container separado |
| ZIP incluía cache Python | Ruído e artefatos desnecessários | Entrega sem __pycache__, pyc, ambientes e segredos novos |

## Interface entregue

A aplicação recebeu o nome visual **Atlas**, com navegação lateral, cards,
tabelas, formulários e mensagens em português. Nenhuma funcionalidade de negócio
existente foi retirada. A interface de terminal continua disponível; o servidor
passa a iniciar a web por padrão.

Foram acrescentados: edição completa de vulnerabilidade, vínculo opcional do
responsável a uma conta, filtros, exportação JSON autenticada, gráficos da
composição do risco, visualização de transmissão entre ativos, matrizes com
rótulos e equações por equipamento. Os gráficos são construídos a partir dos
resultados calculados, sem valores fixos de demonstração.

O CSS e o JavaScript são locais, sem build de frontend ou dependência de CDN.
Flask/Jinja cuidam da interface, Gunicorn da execução HTTP e NumPy do modelo
matemático. A separação facilita explicar as decisões durante a apresentação.

## Ressalvas de modelagem e operação

1. **CVSS versus risco:** a nota CVSS é uma severidade; o índice de risco pode
   exceder 10. Pesos qualitativos são uma escala local documentada, não conversão
   oficial. Não avaliada bloqueia a análise.
2. **Tratamento da falha:** o modelo implementado soma todos os registros,
   inclusive corrigidos, por interpretação literal do enunciado. Não há fator de
   mitigação definido no PDF. Isso é mostrado nas telas e nos testes.
3. **Colunas de M:** uma coluna por ocorrência cadastrada no ativo. CVEs iguais em
   ativos distintos são ocorrências separadas, permitindo avaliações diferentes.
   Se o docente exigir um catálogo global de vulnerabilidades deduplicadas,
   essa identificação deverá ser ajustada; os produtos b e x são equivalentes
   quando as severidades das ocorrências correspondentes são iguais.
4. **Polimorfismo:** existe em tipos e sugestões de categorias. O fator de
   exposição por tipo é uma sugestão do PDF, não requisito obrigatório, e não
   foi acrescentado à equação obrigatória b=Mv.
5. **Autorização:** todos os usuários autenticados editam o inventário comum.
   Apenas a própria conta pode ser alterada/excluída. Não há papéis administrativos,
   ACL por ativo, recuperação de senha por email ou login institucional.
6. **Autoria não é log imutável:** há criador e último editor. Não há trilha de
   todos os eventos de exclusão/alteração. IDs ajudam a preservar identidade,
   mas não substituem auditoria corporativa.
7. **Escala:** solução para inventário acadêmico pequeno. JSON é adequado ao
   requisito, mas não substitui um banco transacional em grande escala. Use um
   worker para o estado temporário da NVD e do limitador de login. Não execute CLI
   e web escrevendo na mesma base ao mesmo tempo.
8. **Disponibilidade:** healthcheck verifica resposta e leitura dos dados. A
   disponibilidade das 24 horas depende também do host, rede, armazenamento,
   permissões e operação do servidor, que não estão sob controle do código.

## Próximo passo concreto

Suba os arquivos revisados numa branch, observe os dois jobs do CI, execute o
roteiro manual e siga `docs/SERVIDOR.md`. Após a implantação e a janela real de
24 horas com evidências, reavalie o requisito 3 com o docente.

O PDF prevê apresentação de cinco minutos e avaliação do domínio do código.
Prepare-se para explicar composição/herança, a persistência em array JSON,
a direção de A, a diferença entre b e x, a verificação de invertibilidade,
a migração de senhas e o papel do container/volume.


## Verificação após reorganização em pacotes

A reorganização moveu módulos para `app/`, testes para `tests/`, recursos visuais
para `app/templates/` e `app/static/` e a explicação matemática para `docs/`.
Os dados locais ficam em `dados/`; o volume Docker mantém `/dados`.
A suíte foi executada novamente: **214 testes e 10 subtestes aprovados**
(Python 3.12, 26,20 s), incluindo três testes dos novos caminhos e recursos.
O lint crítico apresentou zero erros. A medição de cobertura apresentada acima
pertence à revisão anterior, não foi recalculada nesta reorganização.

Após a reorganização, também passaram os testes de navegador desktop/mobile,
CRUD e CVSS, HTTP real com Gunicorn, persistência após reinício e monitor curto.
Docker e execução real de 24 horas continuam pendentes no servidor.
