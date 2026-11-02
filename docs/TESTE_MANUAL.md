# Roteiro de aceitação da interface

Execute em uma base de teste. Cada operação deve mostrar confirmação ou uma
mensagem clara de validação. Não use os dados originais para testar exclusões.

## 1. Entrar e cadastrar os ativos

Crie a conta `apresentacao` com uma senha escolhida por você. Entre no sistema.
Crie também outra conta pela tela Usuários, se quiser demonstrar troca de autor.

Na tela **Ativos**, cadastre os registros abaixo. Selecione a conta criada como
responsável vinculado. Use status **Ativo** nos três.

| ID | Nome | Tipo | Localização |
| --- | --- | --- | --- |
| 1 | Servidor-Web | Serviço | Laboratório 1 |
| 2 | Banco-Dados | Banco de dados | Datacenter |
| 3 | Roteador | Dispositivo de rede | Sala de redes |

Confirme listagem e busca por `1`, `Servidor` e `Banco`. Edite uma descrição e
confirme a atualização. Tente cadastrar ID 1 novamente e nome `servidor-web` com
outro ID: as duplicidades devem ser recusadas.

## 2. Cadastrar as vulnerabilidades

Abra cada ativo e escolha **Cadastrar vulnerabilidade**. Não preencha CVE/vetor
nesta primeira parte. Use tratamento **Aberta**.

| Ativo | Descrição | Categoria | Severidade |
| --- | --- | --- | --- |
| Servidor-Web | Configuração insegura do serviço | Configuração | Alta |
| Banco-Dados | Permissões excessivas no banco | Controle de acesso | Média |
| Roteador | Informações de versão expostas | Exposição de informações | Baixa |

Na análise de risco, sem dependências, os valores próprios e efetivos devem ser
8, 5 e 2. O risco herdado deve ser zero.

## 3. Cadastrar as dependências

Na tela **Dependências**, informe exatamente esta direção:

| Ativo que recebe o risco | Origem do risco | Peso |
| --- | --- | --- |
| Servidor-Web | Banco-Dados | 0,25 |
| Servidor-Web | Roteador | 0,10 |
| Banco-Dados | Roteador | 0,50 |

A seta do desenho vai da **origem** para quem **recebe** o risco.
Confira em **Análise de risco**:

| Ativo | Próprio | Herdado | Efetivo |
| --- | ---: | ---: | ---: |
| Servidor-Web | 8,00 | 1,70 | 9,70 |
| Banco-Dados | 5,00 | 1,00 | 6,00 |
| Roteador | 2,00 | 0,00 | 2,00 |

Posto esperado: 3/3. Determinante: 1. A matriz M é a identidade nesse cenário.
Explique a primeira equação: 8 + 0,25 × 6 + 0,10 × 2 = 9,70.

Tente autodependência, peso 1, peso negativo e atualizar Web→Banco para 0,95
mantendo Web→Roteador 0,10: devem ser recusados sem alterar os dados anteriores.

## 4. Calcular e aplicar CVSS

Em **Calcular CVSS**, cole:

```text
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
```

Resultado: **9,8 / Crítica**. Aplique à vulnerabilidade do Servidor-Web.
A severidade deve acompanhar a nota automaticamente. O risco próprio do Web
passa a 9,8 e o efetivo passa a **11,5**; os demais continuam 6 e 2.

Edite o tratamento dessa vulnerabilidade para **Corrigida**. O risco permanece
11,5 porque o modelo inclui todos os registros. Isso deve ser explicado, não
apresentado como efeito de mitigação.

## 5. Consultar CVE, se houver internet

Consulte `CVE-2021-44228`. A descrição e avaliações são obtidas da NVD naquele
momento, por isso não fixe uma fonte/nota esperada no roteiro. Cadastre um quarto
ativo fictício, confira o resultado e importe uma avaliação para ele.

Veja fonte, versão, vetor, consulta e autor no detalhe do registro. Uma segunda
importação do mesmo CVE para o mesmo ativo deve ser recusada. Sem nota compatível,
a vulnerabilidade deve ficar **Não avaliada**, impedindo o risco até receber uma
avaliação. Indisponibilidade de rede deve gerar mensagem sem interromper o CRUD.

## 6. Contas, edição simultânea e persistência

1. Altere seu login e confira que o ID e os vínculos de responsabilidade continuam.
2. Entre com outra conta e edite uma vulnerabilidade: criador preservado, último
   editor atualizado.
3. Abra duas abas de edição. Salve a primeira e tente salvar a segunda: a segunda
   deve mostrar conflito e solicitar recarga, sem sobrescrever a primeira.
4. Altere a senha: as sessões antigas devem pedir novo login. A senha anterior
   não deve mais autenticar.
5. Reinicie a aplicação/container antes de começar a prova das 24 horas e confirme
   que contas, ativos, vulnerabilidades e dependências permanecem.
6. Exporte o inventário: o arquivo deve ser uma lista JSON e não conter hashes de
   senha. A aplicação não exporta o arquivo de contas pela interface.

## 7. Exclusões e cenário singular

Somente na base descartável: remova uma dependência e observe o novo risco;
remova uma vulnerabilidade; depois remova um ativo. Referências de dependência ao
ativo excluído também devem desaparecer.

Excluir uma conta exige senha atual e digitar o login; encerra a sessão e
preserva o histórico do inventário. Não exclua sua única conta com o cadastro
fechado se pretende continuar usando a base.

Para testar singularidade, use **outra base isolada**, com uma cópia de
`exemplos/risco_singular.json`, configurando `INVENTARIO_ARQUIVO` antes de iniciar.
A análise deve mostrar impedimento de invertibilidade e risco efetivo indisponível.
Não substitua a base da apresentação por esse exemplo.
