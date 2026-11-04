# Risco efetivo — requisito 4 do Trabalho 2

## Como usar

Abra `python -m app.main` e escolha **7 — Análise de risco e dependências**.
Cadastre os ativos e as vulnerabilidades pelos menus já existentes. No submenu
de risco, a opção **1** define uma dependência e a **4** mostra os riscos de todos
os ativos. A opção **5** exibe as matrizes e os detalhes numéricos.

Ao cadastrar a relação, selecione primeiro **quem recebe o risco** e depois
**de onde ele vem**. Exemplo: se Servidor web depende de Banco de dados com
peso 0,25, o servidor recebe 25% do risco efetivo do banco. Isso não cria a
relação inversa. Digite `0,25` ou `0.25`; não digite `25`.

A opção 1 também altera o peso de uma relação existente. A opção 3 remove uma
relação. Excluir um ativo remove as dependências que apontavam para ele; trocar
o tipo do ativo preserva as relações.

## Modelo implementado

Dados n equipamentos e m registros de vulnerabilidades:

- **M**, n × m: matriz binária de incidência. M[i,j] vale 1 se o registro j
  está associado ao equipamento i, e 0 caso contrário.
- **v**, m entradas: severidade numérica de cada registro.
- **b = M·v**, n entradas: risco próprio de cada equipamento.
- **A**, n × n: A[i,j] é a fração do risco do equipamento j recebida pelo i.
  A diagonal é zero; os pesos devem estar entre 0 (inclusive) e 1 (exclusive).
- **C = I − A**: matriz do sistema.
- **x**, n entradas: solução de C·x = b. Equivalentemente, x = b + A·x.
- **x − b = A·x**: parcela herdada, mostrada como informação adicional.

O programa usa `numpy.linalg.solve(C, b)`, sem calcular explicitamente C⁻¹.
O cálculo é global: calcular cada ativo isoladamente ignoraria dependências
indiretas e ciclos. Depois, o relatório apresenta o resultado individual.

### O que é uma coluna de M neste projeto

O sistema existente armazena cada registro de vulnerabilidade dentro de um
ativo. Por isso, **cada ocorrência cadastrada é uma coluna**. A etiqueta
`000001/V2`, por exemplo, significa a segunda vulnerabilidade do ativo 000001.
A ordem dos ativos é crescente por ID, e a ordem das vulnerabilidades é a do
cadastro. IDs não precisam ser consecutivos ou começar em zero.

O mesmo CVE pode aparecer em mais de um ativo, com avaliações locais diferentes;
essas ocorrências são preservadas em colunas distintas. Não se juntam registros
apenas por terem descrições iguais. No caso de notas iguais, essa representação
produz o mesmo b que uma coluna compartilhada, sem exigir uma migração para um
catálogo global de vulnerabilidades. A matriz continua binária e obedece b=M·v.

### Como v é obtido

Se existir uma avaliação CVSS, utiliza-se sua nota exata, incluindo zero. Sem
CVSS, o cadastro qualitativo existente usa a seguinte **política local**:

| Severidade cadastrada | Peso no modelo |
| --- | ---: |
| NENHUMA | 0 |
| BAIXA | 2 |
| MEDIA | 5 |
| ALTA | 8 |
| CRITICA | 10 |
| NAO_AVALIADA | Bloqueia o cálculo e identifica o registro pendente |

Essa escala foi escolhida nesta implementação para compatibilidade com o
cadastro anterior: **não é uma tabela fornecida pelo enunciado nem uma conversão
oficial para CVSS**. Está centralizada em `PESOS_MANUAIS`, em `app/riscos.py`.
Ela não é gravada como se fosse uma nota CVSS. O relatório informa seu uso.
Os números do Enum (1, 2, 3, ...) servem ao menu, não são usados como severidades.

O resultado é um índice acumulado: pode superar 10 e não representa uma
probabilidade ou uma nova nota CVSS. Se houver versões CVSS diferentes, o
programa avisa que está somando as notas cadastradas sem conversão entre versões.

### Status e fatores de exposição

O modelo segue a fórmula literal do enunciado, considerando **todos os registros
associados**, inclusive CORRIGIDA e ACEITA_COMO_RISCO, e todos os status de ativo.
Não foi acrescentado um filtro de tratamento ou um fator de redução implícito.
Assim, alterar somente o status não muda o risco matemático neste modelo.
Remover a associação de uma vulnerabilidade muda M e b; aplicar uma nova nota
CVSS muda v e b. O relatório informa essa regra para não sugerir uma redução que
não foi calculada.

O fator de exposição por tipo é uma sugestão opcional do PDF. Não foram
introduzidos multiplicadores arbitrários: o fator de todos os tipos é
implicitamente 1, preservando exatamente b=M·v. A hierarquia e o polimorfismo
existentes no projeto foram mantidos.

## Invertibilidade e precisão

Ao criar/alterar uma dependência, o sistema exige **soma dos pesos da linha < 1**.
Com pesos não negativos e Aii=0, isso torna I−A estritamente diagonal dominante
e garante invertibilidade. A soma é calculada com `math.fsum`; uma alteração
inválida não substitui o peso anterior.

A leitura do JSON valida formato, IDs, referências, pesos, duplicações e diagonal.
Ela preserva relações estruturalmente válidas cuja soma seja >= 1, para que bases
importadas possam ser diagnosticadas e corrigidas pelo menu. A falta de dominância
diagonal, sozinha, não prova singularidade.

Antes de resolver, o analisador:

1. Verifica o **posto de I−A** com `numpy.linalg.matrix_rank`, baseado em SVD.
   A tolerância padrão é proporcional ao maior valor singular, à dimensão e à
   precisão do tipo float. Posto menor que n significa ausência de invertibilidade
   na precisão utilizada. Nesse caso, exibe b e não chama `solve`.
2. Calcula o **número de condição** com `numpy.linalg.cond` (norma 2). Valor
   >= 10⁸ gera aviso; >= 10¹², ou infinito, bloqueia a solução por baixa
   confiabilidade. Esses limites são políticas numéricas da implementação,
   documentadas como constantes em `app/riscos.py`, não exigências do enunciado.
3. Mostra o determinante **apenas para diagnóstico**. Não usa `det == 0` nem
   considera que todo determinante pequeno significa singularidade.
4. Resolve diretamente e verifica se x é finito e o resíduo relativo é <= 10⁻¹⁰:
   ||C·x − b||∞ / (||C||∞·||x||∞ + ||b||∞). Se ambos os termos forem zero,
   considera o resíduo zero. O resíduo pequeno não elimina o problema de uma
   matriz mal condicionada; por isso ambos são analisados.

Soluções negativas de bases importadas são exibidas com aviso explícito: são
soluções algébricas, mas não podem ser interpretadas como risco. Os valores não
são truncados nem corrigidos silenciosamente. Corrija os pesos pelo menu.
No cadastro normal, a regra de soma < 1 evita esse problema.

## Persistência e orientação a objetos

O JSON permanece um **array de objetos**, um por ativo. Cada objeto recebe um
campo opcional como este:

```json
"dependencias": [
    {"id_origem": 2, "peso": 0.25},
    {"id_origem": 3, "peso": 0.10}
]
```

Se esse campo estiver no ativo 1, ele recebe 25% do risco de 2 e 10% do risco de 3.
Bases antigas sem o campo são lidas com lista vazia. O arquivo de dados original
entregue pelo usuário não foi substituído por exemplos.

- `Dependencia`: objeto imutável que valida ID e peso.
- `Equipamento`: possui suas vulnerabilidades e dependências por composição.
- `Inventario`: controla relações entre ativos, remoção e acesso ao cálculo.
- `ArmazenamentoJSON`: salva/carrega os objetos e verifica referências existentes.
- `AnalisadorRisco`: monta M, v, A, b e resolve o sistema sem acessar terminal/rede.
- `ModeloRisco` e `ResultadoRisco`: transportam matrizes, resultados e diagnóstico.
- `MenuRiscos`: recebe entradas e apresenta o resultado.

Os resultados não são persistidos: cada consulta refaz o cálculo sobre o estado
atual do inventário, reconstruído do JSON ao iniciar. Isso evita valores antigos
após uma mudança de vulnerabilidade ou dependência.

## Cenário de três equipamentos, resolvido à mão

Use uma cópia do exemplo para preservar o original durante a demonstração:

```bash
cp exemplos/risco_tres_ativos.json /tmp/risco-demo.json
INVENTARIO_ARQUIVO=/tmp/risco-demo.json python -m app.main
```

Escolha **7 → 4** para os resultados ou **7 → 5** para as matrizes.
O exemplo usa as severidades locais ALTA, MEDIA e BAIXA, respectivamente:

| ID | Equipamento | Risco próprio | Dependências |
| --- | --- | ---: | --- |
| 1 | Servidor web | 8 | Banco: 0,25; Roteador: 0,10 |
| 2 | Banco de dados | 5 | Roteador: 0,50 |
| 3 | Roteador | 2 | Nenhuma |

M é a identidade 3 × 3, v=(8,5,2) e b=(8,5,2).

| A: linha recebe da coluna | Servidor web | Banco de dados | Roteador |
| --- | ---: | ---: | ---: |
| Servidor web | 0 | 0,25 | 0,10 |
| Banco de dados | 0 | 0 | 0,50 |
| Roteador | 0 | 0 | 0 |

As equações e suas soluções são:

- x₃ = 2.
- x₂ = 5 + 0,50·x₃ = 5 + 1 = **6**.
- x₁ = 8 + 0,25·x₂ + 0,10·x₃ = 8 + 1,50 + 0,20 = **9,70**.

| Equipamento | Próprio | Herdado | Efetivo |
| --- | ---: | ---: | ---: |
| Servidor web | 8 | 1,70 | 9,70 |
| Banco de dados | 5 | 1 | 6 |
| Roteador | 2 | 0 | 2 |

I−A é triangular com diagonal (1,1,1), então seu determinante é 1 e seu posto é 3.
Observe que o servidor herda uma parte do risco do roteador indiretamente pelo
banco e outra parte pela ligação direta. Usar b no lugar de x na propagação
perderia o caminho indireto.

### Exemplo sem invertibilidade

```bash
cp exemplos/risco_singular.json /tmp/risco-singular-demo.json
INVENTARIO_ARQUIVO=/tmp/risco-singular-demo.json python -m app.main
```

Nesse arquivo importado, cada um dos três equipamentos recebe 0,5 dos outros
dois. Cada linha de A soma 1. Logo, A·(1,1,1)=(1,1,1) e
(I−A)·(1,1,1)=(0,0,0): existe vetor não nulo no núcleo, portanto I−A não é
invertível. O programa exibe os riscos próprios e a mensagem de impedimento;
o risco efetivo fica indisponível. O cadastro normal impede criar essa soma.

### Exemplo com ciclo que funciona

Um ciclo não implica singularidade. Para b=(8,5), A₁₂=0,5 e A₂₁=0,25:

- x₁ = 8 + 0,5·x₂;
- x₂ = 5 + 0,25·x₁;
- substituindo: 0,875·x₁ = 10,5 ⇒ **x₁=12** e **x₂=8**.

Esse caso também faz parte dos testes automatizados.

## Roteiro curto para a apresentação

1. Abra o exemplo de três ativos e mostre as dependências.
2. Consulte os riscos e explique a diferença entre próprio e herdado.
3. Mostre M, v e A; explique que A[i,j] transmite risco de j para i.
4. Explique por que se resolve (I−A)x=b e por que não se calcula a inversa.
5. Mostre o diagnóstico e o exemplo singular; mencione a tolerância e o número
   de condição. Execute os testes se houver tempo.

O enunciado avalia sua capacidade de explicar as decisões. Estude principalmente
a direção das dependências, a construção de b, o efeito dos ciclos e a diferença
entre singularidade matemática e baixa confiabilidade numérica.

## Testes e container

`python -m pytest -q` executa a suíte completa, incluindo os testes em
`tests/test_riscos.py`. Eles verificam o exemplo manual, ciclos, ausência de falhas,
CVSS versus escala local, bloqueios numéricos, JSON antigo, referências inválidas,
remoção, troca de tipo e navegação real dos menus com entradas simuladas.

`numpy==2.3.5` está em `requirements.txt`, utilizado também pelo Dockerfile.
O README explica a execução em container e a verificação das 24 horas no servidor.
A comprovação desse período depende dos registros coletados em cada implantação;
os testes automatizados não substituem a execução real no servidor.
