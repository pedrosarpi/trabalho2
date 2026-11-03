# Executar no servidor da disciplina e verificar 24 horas

Guia baseado no requisito 3 de `Trabalho_2.pdf` e na imagem de acesso SSH
fornecidos. O PDF exige execução em container por **pelo menos 24 horas** em
servidor estável. A imagem informa **10.0.99.150**, com a matrícula como usuário
**e senha inicial do SSH**. O código de matrícula mostrado na imagem é só exemplo.

Os comandos abaixo devem ser executados por você, com sua matrícula. Não houve
acesso ao servidor nesta revisão. A disponibilidade de Docker, Compose, porta,
internet e espaço em disco precisa ser conferida no ambiente da faculdade.

## 1. Testar SSH a partir do Fedora ou PowerShell

```bash
ssh SUA_MATRICULA@10.0.99.150
```

Substitua `SUA_MATRICULA`. Quando a senha for solicitada, digite sua matrícula
novamente, conforme a orientação recebida. O terminal não mostra os caracteres
da senha. No primeiro acesso, confira a identificação do servidor com o docente
antes de aceitar uma chave desconhecida.

O IP é privado: use a rede da faculdade ou a VPN indicada por ela. Se ocorrer
erro, registre a mensagem e informe ao docente, como pede a imagem. Não suponha
que seja problema do programa.

Depois de entrar, execute no servidor:

```bash
whoami
python3 --version
docker --version
docker compose version
docker info
```

Se faltar permissão ou algum componente, solicite a configuração ao docente.
Não é necessário instalar as bibliotecas Python no host: elas entram na imagem.
O Python do host é utilizado pelos scripts de configuração e monitoramento.

## 2. Levar o projeto para sua pasta

Opção A: após subir a nova versão para sua branch, no servidor:

```bash
git clone --branch interface-web URL_DO_SEU_REPOSITORIO trabalho2-web
cd trabalho2-web
```

Use o nome real da sua branch. Se o repositório for privado, configure o acesso
Git adequado; não coloque tokens em comandos compartilhados ou no README.

Opção B: transfira o ZIP desta entrega do seu computador:

```bash
scp trabalho2-web-organizado.zip SUA_MATRICULA@10.0.99.150:~/
```

Então, no servidor:

```bash
mkdir -p ~/entrega-web
python3 -m zipfile -e ~/trabalho2-web-organizado.zip ~/entrega-web
cd ~/entrega-web/trabalho2-web
```

Execute os comandos seguintes na pasta que contém `compose.yaml`.

## 3. Configurar e iniciar

Confirme com o docente qual porta você pode usar. Este guia usa **18080** como
exemplo; ela precisa estar disponível. Verifique, se o comando estiver instalado:

```bash
ss -ltn
```

Escolha um nome de projeto **único no servidor**, usando sua matrícula em letras
minúsculas. Isso evita que alunos com acesso ao mesmo Docker compartilhem por
engano containers e volumes com o mesmo nome.

```bash
python3 scripts/configurar.py --projeto inventario-sua-matricula --porta 18080
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
curl --fail http://127.0.0.1:18080/healthz
```

Resultado esperado: serviço `inventario` em execução e **healthy**. A consulta de
saúde deve retornar `"status":"ok"`, uptime e identificador da instância. Se não
houver `curl`, use:

```bash
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:18080/healthz').read().decode())"
```

O script cria `.env` e não o sobrescreve. Se ele já existir, confira seus valores
em seu editor privado. Não publique `.env`, não use `docker compose config` sem
`--quiet` em material de apresentação e não salve `docker inspect` completo:
essas saídas podem incluir segredos.

A primeira construção precisa de acesso à imagem Python e ao índice de pacotes.
A consulta CVE precisa de acesso à NVD. Sem internet, CRUD, CVSS e risco continuam
funcionando depois que as dependências estão instaladas.

## 4. Abrir a interface no seu computador

O Compose publica a porta somente em `127.0.0.1` do servidor. Em **outro terminal
no seu computador**, mantenha este túnel aberto:

```bash
ssh -N -L 18080:127.0.0.1:18080 SUA_MATRICULA@10.0.99.150
```

Abra **http://127.0.0.1:18080** no navegador do seu computador. Crie sua conta da
aplicação. A senha SSH não é importada para ela.

Se a porta local 18080 estiver ocupada, use outra à esquerda:

```bash
ssh -N -L 18081:127.0.0.1:18080 SUA_MATRICULA@10.0.99.150
```

Nesse caso, abra **http://127.0.0.1:18081**. A porta à direita continua sendo a
porta configurada no servidor. O túnel não precisa permanecer aberto durante as
24 horas; o container e o monitor devem permanecer rodando no servidor.

Se o docente exigir acesso direto por IP/navegador de outra máquina, combine
porta, firewall e HTTPS com ele antes de alterar a publicação. Para HTTPS real,
configure `COOKIE_SEGURO=true`. No túnel HTTP local, mantenha `false`, pois o
navegador acessa HTTP e o transporte até o servidor é protegido pelo SSH.

## 5. Testar antes de começar a contagem

Siga `docs/TESTE_MANUAL.md`. Crie uma conta, três ativos, vulnerabilidades e
relações. Confira os riscos esperados **9,70 / 6,00 / 2,00**.

Teste a persistência **antes** do período de 24 horas:

```bash
docker compose restart inventario
docker compose ps
```

Aguarde voltar a `healthy`, atualize o navegador, faça login se necessário e
confirme ativos, vulnerabilidades, dependências e conta. O volume guarda ambos os
JSON. Recriar o container com `docker compose up -d` também mantém esse volume.

Pare de editar a configuração e de reiniciar a aplicação quando iniciar a coleta
que pretende apresentar como evidência de continuidade.

## 6. Registrar as 24 horas no próprio servidor

Mantenha o `.env` e a pasta do projeto durante todo o período. Inicie apenas
quando o container estiver saudável:

```bash
mkdir -p evidencias
CID=$(docker compose ps -q inventario)
date -u > evidencias/inicio.txt
docker compose ps > evidencias/container-inicio.txt
docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.RestartCount}}' "$CID" > evidencias/estado-inicio.txt
nohup python3 -u scripts/monitorar_24h.py --url http://127.0.0.1:18080/healthz --horas 24 --intervalo 60 --container "$CID" --saida evidencias/monitoramento-24h.jsonl > evidencias/monitoramento.log 2>&1 < /dev/null &
echo $! > evidencias/monitoramento.pid
```

Esses comandos usam a porta 18080. Ajuste `--url` se escolheu outra. O monitor usa
somente a biblioteca padrão do Python e consulta Docker com o mesmo usuário SSH.
Ele registra uma amostra imediatamente e a última após pelo menos 24 horas.

Acompanhe quando quiser:

```bash
tail -n 5 evidencias/monitoramento.log
docker compose ps
docker compose logs --tail=50 inventario
```

Depois de completar o período:

```bash
cat evidencias/monitoramento-24h.resumo.json
date -u > evidencias/fim.txt
docker compose ps > evidencias/container-fim.txt
docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.RestartCount}}' "$CID" > evidencias/estado-fim.txt
docker compose logs --no-color --since 25h inventario > evidencias/container.log
```

Se reconectou por SSH e perdeu a variável `CID`, execute novamente
`CID=$(docker compose ps -q inventario)` antes do `inspect`; os arquivos do início
e o monitor mantêm a identidade original para comparação.

O resumo precisa mostrar:

- `duracao_segundos` >= 86400;
- `falhas: 0` e `reinicios_detectados: 0`;
- `container_verificado: true`;
- `evidencia_24h: true`.

Esse resultado é **evidência amostral**, acompanhada de uptime e identidade do
processo/container; não prova ausência de uma indisponibilidade muito curta entre
amostras. Apresente também os estados inicial/final e logs. O docente determina
qual evidência aceitar.

Se houver falhas, reinício, resumo ausente ou monitor interrompido, investigue e
faça uma nova coleta completa, usando outro nome em `--saida`. Não edite o log
para ocultar falhas. Se o monitor rodar menos de 24 horas ou sem `--container`,
ele não marca `evidencia_24h` como verdadeira. Os testes automatizados que simulam
o tempo não são evidência de execução real.

`restart: unless-stopped` ajuda a retomar após saída do processo; um healthcheck
ruim, sozinho, **não provoca reinício automático** no Docker. Após reinício da
máquina, o container pode voltar, mas o monitor iniciado com `nohup` não volta
sozinho e a continuidade deve ser reavaliada.

## 7. Backup e migração dos dados locais

A imagem não inclui suas contas/dados locais. O ZIP preserva os JSON enviados
para permitir continuidade local, mas eles estão no `.gitignore` e `.dockerignore`.
Não os suba como dados de demonstração públicos.

Antes de restaurar ou migrar, pare o serviço e faça uma cópia do volume atual:

```bash
docker compose stop inventario
mkdir -p backups/antes-da-migracao
docker compose cp inventario:/dados/. backups/antes-da-migracao/
```

Use um destino novo para cada backup. A cópia contém hashes de senha: mantenha-a
privada. Para importar seus `usuarios.json` e `vulnerabilidades.json` locais em
uma base nova (ou substituir intencionalmente a base após o backup):

```bash
docker compose cp dados/usuarios.json inventario:/dados/usuarios.json
docker compose cp dados/vulnerabilidades.json inventario:/dados/vulnerabilidades.json
docker compose run --rm --no-deps --user 0 inventario chown -R 10001:10001 /dados
docker compose up -d --wait --wait-timeout 180
```

O ajuste de dono ocorre apenas no volume `/dados`, dentro do container. Ele
permite que o usuário sem privilégios da aplicação grave arquivos copiados.
Se qualquer arquivo for inválido, a aplicação informa erro e não o zera; restaure
a cópia ou corrija o arquivo com o serviço parado. O SHA-256 legado migra para
scrypt no próximo login válido. Repita o teste de persistência após a migração.

Para baixar evidências ao seu computador:

```bash
scp -r SUA_MATRICULA@10.0.99.150:~/entrega-web/trabalho2-web/evidencias ./evidencias-servidor
```

Adapte o caminho se usou `git clone` em outra pasta.

## 8. Comandos úteis e falhas comuns

| Situação | Verificação/ação |
| --- | --- |
| SSH não conecta | Rede/VPN, IP e mensagem exata; encaminhar ao docente |
| Permission denied no SSH | Matrícula correta e senha inicial informada na imagem |
| Docker indisponível/sem permissão | Conferir `docker info` e solicitar ajuste ao docente |
| Porta em uso | Escolher porta livre/autorizada e atualizar `.env`, túnel e monitor |
| Container não inicia | `docker compose logs --tail=100 inventario`; conferir SECRET_KEY e construção |
| 503 / dados inválidos | Conferir JSON, permissões e espaço; preservar backup, não apagar a base |
| Formulário expirado / conflito | Recarregar a página e refazer a operação com os dados atuais |
| NVD fora do ar ou limitada | Tentar mais tarde; usar cadastro manual/calculadora offline |
| Não há resumo das 24h | Monitor ainda executando ou interrompido; conferir seu log/PID |

Encerrar após a avaliação: `docker compose stop`. Remover containers mantendo os
dados: `docker compose down`. **`docker compose down -v` apaga o volume**, por isso
não o use no servidor de apresentação. Ele aparece somente no ambiente descartável
do CI.

## 9. Subir uma branch sem alterar a main

No seu clone local, extraia/copie os arquivos de código desta entrega sobre a
pasta de trabalho da branch. Preserve a pasta `.git` do clone; não faça outro
`git init`. Antes de copiar, salve suas alterações atuais em um commit ou backup.

```bash
git status
git switch -c interface-web
# Copie os arquivos revisados e execute os testes indicados no README.
git status
```

Confira se dados pessoais/segredos já eram rastreados. O `.gitignore` não remove
arquivos que já entraram no Git:

```bash
git ls-files usuarios.json vulnerabilidades.json .env
```

Se aparecerem, remova-os **somente do índice**, preservando as cópias locais:

```bash
git rm --cached --ignore-unmatch usuarios.json vulnerabilidades.json .env
git add .
git diff --cached --stat
git commit -m "Adiciona interface web e revisa persistencia, contas e implantacao"
git push -u origin interface-web
```

Inspecione as alterações antes do commit. Se credenciais já foram publicadas,
tire os arquivos das próximas versões e troque as senhas/chaves expostas. Não é
necessário fazer merge para testar o CI da branch.


### Atualizar um clone que ainda usa a estrutura antiga

A estrutura desta entrega está descrita no README. Ao copiar os arquivos para
seu clone Git, retire os antigos módulos Python e `test_*.py` da raiz, além das
pastas `templates/` e `static/` antigas, depois de conferir suas versões novas
em `app/` e `tests/`. Preserve `.git`, seu `.env` e seus dados atuais.
Não deixe cópias antigas do código junto das novas. Confira os movimentos/
exclusões em `git status` e execute os testes antes de criar o commit.
