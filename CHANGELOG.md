# Histórico de alterações

## 1.0.1 — 04/11/2026

Atualização de manutenção sobre a release 1.0.0.

### Correções

- Corrigida a atribuição de fonte CVSS ao trocar ou remover o CVE de uma
  vulnerabilidade. A avaliação mantida passa a cálculo local, sem atribuição
  indevida à fonte do registro anterior.
- Monitor de 24 horas registra respostas inválidas e conexões HTTP interrompidas,
  sem encerrar silenciosamente a coleta nem aprovar um período com falhas.
- Teste do cenário singular independente do diretório de execução.

### Configuração e documentação

- Incluídos `.dockerignore` e `.env.example`; ampliado o `.gitignore`.
- Porta padrão do Compose, configurador e monitor alinhada em **2201**.
  `PORTA_WEB` de um `.env` existente continua tendo prioridade.
- Exemplos explicam **8000 no container**, **2201 no servidor** e **18080
  no túnel local**, sem divulgar matrícula ou endereço da instituição.
- Guia com atalho `ssh orthocrud`, uso de sudo e coleta de evidências.
- CI em pushes/PRs, Python 3.11/3.12 e job de build/teste do container.
- Auditoria reescrita com os resultados desta revisão.
- Removido `docs/VALIDACAO.json`: duplicava resultados antigos e não descrevia
  a release atual.

### Validação

220 testes e 10 subtestes aprovados em Python 3.12.14; lint crítico sem erros.
Teste HTTP e persistência após recriar a aplicação aprovados. Docker não foi
executado no ambiente de revisão; confirme o job de container no GitHub.

### Atualizar uma instalação

1. Faça backup dos dados e preserve `.env` e o nome `COMPOSE_PROJECT_NAME`.
2. Atualize o código mantendo os arquivos privados fora do Git. Se copiar os
   arquivos por cima, remova também `docs/VALIDACAO.json`.
3. Confira o `git diff`, execute os testes e publique uma **nova tag v1.0.1**,
   preservando a tag v1.0.0.
4. No servidor, fora da janela de coleta de 24 horas, aplique com
   `sudo docker compose up -d --build --wait --wait-timeout 220` e confira
   `/healthz` na porta configurada.

Não há mudança no formato JSON nem migração de dados. Uma mudança de porta
ou reconstrução pode recriar o container e interromper a execução contínua.

## 1.0.0

Primeira release do OrthoCRUD: usuários, ativos, vulnerabilidades, CVE/CVSS,
dependências e risco efetivo, com interfaces web/terminal e implantação Docker.

