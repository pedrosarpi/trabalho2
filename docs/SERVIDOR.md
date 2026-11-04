# OrthoCRUD — guia simples de acesso ao servidor

Este guia usa a configuração informada nesta instalação. Execute os comandos
um por vez; se houver erro, resolva antes de continuar.

## 1. Entenda os endereços

| Item | Valor | Para que serve |
| --- | --- | --- |
| Servidor da faculdade | `10.0.99.150` | Computador onde o programa está rodando |
| Usuário SSH | `12621CBS201` | Sua conta de acesso ao servidor |
| Pasta no servidor | `~/trabalho2` | Local do código e do Compose |
| Projeto Docker Compose | `orthocrud` | Identifica os containers e o volume desta instalação |
| Porta no servidor | **2201** | Acesso ao programa a partir do próprio servidor |
| Porta no seu computador | **18080** | Entrada do túnel que você abre no navegador |
| Porta dentro do container | **8000** | Porta usada pela aplicação dentro do Docker |

**18080 foi escolhida como exemplo para o seu computador; não é uma exigência
da faculdade.** Ela pode ser diferente da porta 2201 do servidor.

O caminho do acesso é: navegador na porta **18080** do seu computador →
túnel SSH → porta **2201** no servidor → aplicação na porta **8000** do container.

O endereço `127.0.0.1` significa “este computador”. No navegador, refere-se à sua
máquina; nos comandos executados por SSH, refere-se ao servidor.

## 2. Para abrir o site no dia a dia

Se o container já está funcionando, basta seguir estes passos.

**No seu computador**, abra um terminal e execute:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 18080:127.0.0.1:2201 12621CBS201@10.0.99.150
```

Informe sua senha do servidor. É normal não aparecerem caracteres ao digitar.
Depois de conectar, o terminal fica sem um novo prompt: ele está mantendo o
túnel aberto.

**No navegador do seu computador**, abra:

**http://127.0.0.1:18080**

Mantenha o terminal do túnel aberto enquanto usar o site. Para fechar o acesso,
pressione **Ctrl+C** nesse terminal. Isso não para o programa no servidor.

Não é necessário executar Docker novamente a cada acesso. Você precisa estar
na rede da faculdade ou em uma VPN que permita alcançar o servidor.
Estar no Wi-Fi não garante, sozinho, que a rede permita a conexão SSH.

### Se 18080 estiver ocupada no seu computador

Se o túnel já estiver aberto em outro terminal, use esse acesso.
Caso precise de outra porta local, use, por exemplo, 18081:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 18081:127.0.0.1:2201 12621CBS201@10.0.99.150
```

Nesse caso, abra **http://127.0.0.1:18081**. A porta do servidor continua sendo
**2201**; não altere o `.env` por causa de uma porta local ocupada.

### Posso usar pelo celular?

A interface é adaptada a telas pequenas. Porém, a configuração atual publica
o serviço somente em `127.0.0.1` do servidor: o acesso remoto exige túnel SSH,
inclusive no celular.

Abrir diretamente `http://10.0.99.150:2201` exige mudar a publicação da porta
e verificar as permissões de rede e firewall com o professor. Não faça essa
mudança durante uma coleta de 24 horas: aplicá-la pode recriar o container.

## 3. Entrar no terminal do servidor

Use isto para consultar o estado, iniciar ou administrar o programa.
**Execute no seu computador:**

```bash
ssh 12621CBS201@10.0.99.150
```

Após entrar, o prompt deve mostrar seu usuário e o nome do servidor, como
`12621CBS201@ciberseguraca`. Então execute:

```bash
cd ~/trabalho2
sudo docker compose ps
```

`Up` indica que o container está rodando. `healthy` indica que a verificação
de saúde está passando. Para testar a aplicação **no servidor**:

```bash
curl --fail http://127.0.0.1:2201/healthz
```

O resultado esperado contém `"status":"ok"`.

Para sair do servidor e voltar ao terminal da sua máquina:

```bash
exit
```

## 4. Iniciar o programa, se ainda não estiver rodando

**No servidor, dentro de `~/trabalho2`:**

```bash
grep -E '^(COMPOSE_PROJECT_NAME|PORTA_WEB)=' .env
```

Na instalação atual, os valores são:

```text
COMPOSE_PROJECT_NAME=orthocrud
PORTA_WEB=2201
```

**Se o `.env` já existe, não execute novamente o script de configuração.**
A mensagem `File exists: '.env'` significa que o script preservou a configuração
existente. Não apague esse arquivo: ele contém a chave de sessão da aplicação.

Somente em uma instalação nova, sem `.env`, gere-o com:

```bash
python3 scripts/configurar.py --projeto orthocrud --porta 2201
```

O nome e a porta devem estar disponíveis e autorizados. Em outra instalação
compartilhada, use um nome de projeto único. Na instalação existente, mantenha
`orthocrud` para continuar usando o mesmo volume de dados.

Para construir e iniciar:

```bash
sudo docker compose config --quiet
sudo docker compose up -d --build --wait --wait-timeout 220
sudo docker compose ps
curl --fail http://127.0.0.1:2201/healthz
```

O primeiro comando não imprime nada quando a configuração é válida.
O `-d` mantém o programa em segundo plano no servidor.
O `--wait-timeout 220` é um tempo de espera em segundos, não uma porta.

Usamos `sudo` porque o usuário desta instalação recebeu erro de permissão ao
acessar o Docker sem ele. Se solicitado, informe a senha do seu usuário no
servidor. Se o `sudo` negar autorização, solicite ajuda ao professor.

A primeira construção precisa de internet para baixar a imagem e as dependências.
Depois de iniciar, abra o túnel conforme a seção 2.
As contas da aplicação são separadas da conta SSH: uma base nova exige cadastro
no site.

## 5. Deixar funcionando por 24 horas

O programa executa no servidor da faculdade. Depois de iniciado com `up -d`,
você pode fechar o SSH, fechar o túnel e desligar seu computador.
O servidor precisa permanecer ligado, com o container em execução.

Antes de começar a contagem, teste cadastros e cálculos. Se quiser testar se os
dados persistem após reinício, faça isso **antes** da coleta:

```bash
sudo docker compose restart inventario
```

Aguarde o estado `healthy` e confirme os dados no site. Depois de iniciar a
coleta, não pare, reinicie, atualize ou reconstrua o container.

### Iniciar a coleta de evidências

**No servidor, em `~/trabalho2`**, execute o bloco abaixo uma única vez por coleta:

```bash
sudo -v
CID=$(sudo docker compose ps -q inventario)
PASTA="evidencias/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$PASTA"
date -u > "$PASTA/inicio.txt"
sudo docker compose ps > "$PASTA/container-inicio.txt"
sudo docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.RestartCount}}' "$CID" > "$PASTA/estado-inicio.txt"
sudo -n nohup python3 -u scripts/monitorar_24h.py --url http://127.0.0.1:2201/healthz --horas 24 --intervalo 60 --container "$CID" --saida "$PASTA/monitoramento-24h.jsonl" > "$PASTA/monitoramento.log" 2>&1 < /dev/null &
```

O monitor consulta a aplicação a cada 60 segundos e verifica o container.
Ele também usa `sudo`, pois precisa acessar o Docker.
O `nohup` permite continuar após fechar a sessão SSH; não reinicia o monitor
se o servidor for reiniciado.

**Confirme que começou antes de desconectar:**

```bash
echo "$PASTA"
tail -n 5 "$PASTA/monitoramento.log"
```

Anote o caminho exibido. O log deve mostrar `Amostra 1: OK`; se estiver vazio,
repita a leitura após alguns segundos. Se houver erro, corrija antes de considerar
a coleta iniciada. A contagem da evidência começa ao iniciar o monitor, não
retroativamente quando você iniciou o container.

### Consultar o resultado

Após pelo menos 24 horas, entre novamente no servidor, vá para `~/trabalho2`
e defina o caminho que anotou, substituindo o exemplo:

```bash
PASTA="evidencias/20261103T232141Z"
sudo cat "$PASTA/monitoramento-24h.resumo.json"
```

O resumo deve indicar:

- `duracao_segundos` igual ou maior que **86400**;
- `falhas: 0`;
- `reinicios_detectados: 0`;
- `container_verificado: true`;
- `evidencia_24h: true`.

O resumo só é criado quando a coleta termina. Se não existir, confira
`tail -n 10 "$PASTA/monitoramento.log"`.

Registre também o estado final:

```bash
CID=$(sudo docker compose ps -q inventario)
date -u > "$PASTA/fim.txt"
sudo docker compose ps > "$PASTA/container-fim.txt"
sudo docker inspect --format '{{.Id}} {{.State.StartedAt}} {{.RestartCount}}' "$CID" > "$PASTA/estado-fim.txt"
sudo docker compose logs --no-color --since 25h inventario > "$PASTA/container.log"
```

Esses registros são evidência por amostragem; não garantem a ausência de uma
interrupção muito curta entre consultas. O professor determina quais evidências
aceitar. Se houver falhas ou reinícios, investigue e inicie uma nova coleta
completa, preservando os registros anteriores.

Para permitir que sua conta baixe os arquivos gerados pelo monitor, depois de
concluído, execute no servidor:

```bash
sudo chown -R "$(id -u):$(id -g)" "$PASTA"
```

**No seu computador**, baixe as evidências:

```bash
scp -r 12621CBS201@10.0.99.150:~/trabalho2/evidencias ./evidencias-servidor
```

## 6. Dados, backup e encerramento

O inventário e as contas ficam no volume Docker do servidor. Fechar o navegador,
o túnel ou o SSH não os apaga. Os dados da instalação local do seu computador
não são enviados automaticamente ao servidor.

Para fazer backup, **fora do período de coleta**, execute no servidor:

```bash
sudo docker compose stop inventario
DESTINO="backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$DESTINO"
sudo docker compose cp inventario:/dados/. "$DESTINO/"
sudo docker compose start inventario
```

Guarde o backup em local privado, pois inclui contas e hashes de senha.
Não publique `.env`, JSON reais, backups ou evidências com informações privadas.

| Ação | Comando no servidor, em `~/trabalho2` |
| --- | --- |
| Consultar estado | `sudo docker compose ps` |
| Ver últimas mensagens | `sudo docker compose logs --tail=50 inventario` |
| Parar após a avaliação | `sudo docker compose stop` |
| Retomar um container parado | `sudo docker compose start` |
| Atualizar a imagem após mudar o código | `sudo docker compose up -d --build --wait --wait-timeout 220` |

**Não use `docker compose down -v`: ele remove o volume e seus dados.**
Não troque o nome do projeto no `.env` para renomear visualmente o aplicativo:
isso pode selecionar outro volume.

## 7. Problemas comuns

| Mensagem ou situação | O que conferir |
| --- | --- |
| `File exists: '.env'` | A configuração já existe; preserve-a e siga para a validação |
| `permission denied ... docker.sock` | Use `sudo docker compose ...`; se não autorizado, fale com o professor |
| SSH não conecta | Rede da faculdade/VPN, endereço, usuário e mensagem de erro |
| `Address already in use` ao abrir túnel | A porta local está ocupada; use o túnel existente ou outra porta local |
| Navegador não abre o site | Túnel aberto, endereço local correto e container saudável |
| `curl` falha no servidor | Confira `sudo docker compose ps` e os logs |
| Container não fica `healthy` | Confira logs; não inicie a coleta de 24 horas até corrigir |
| Site sem seus dados locais | O volume do servidor é uma base independente da sua máquina |

**Rotina diária:** abrir o túnel no seu computador → acessar
**http://127.0.0.1:18080** → usar o site → fechar o túnel quando terminar.
