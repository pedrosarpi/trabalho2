"""Questionário das métricas Base CVSS 3.1 e entrada de vetores."""
from seguranca import calcular_cvss
from utilidades import ler_inteiro, ler_texto, mensagem_erro


METRICAS = (
    ('AV', 'Vetor de ataque: de onde o ataque pode ocorrer?',
     [('N', 'Rede'), ('A', 'Rede adjacente'), ('L', 'Local'), ('P', 'Físico')]),
    ('AC', 'Complexidade: depende de condições fora do controle do atacante?',
     [('L', 'Baixa: não'), ('H', 'Alta: sim')]),
    ('PR', 'Privilégios necessários ANTES do ataque:',
     [('N', 'Nenhum'), ('L', 'Baixos'), ('H', 'Altos')]),
    ('UI', 'Interação de outra pessoa é necessária?',
     [('N', 'Não'), ('R', 'Sim')]),
    ('S', 'Escopo: o impacto ultrapassa a autoridade de segurança do componente?',
     [('U', 'Inalterado'), ('C', 'Alterado')]),
    ('C', 'Impacto na confidencialidade:', [('N', 'Nenhum'), ('L', 'Baixo'), ('H', 'Alto')]),
    ('I', 'Impacto na integridade:', [('N', 'Nenhum'), ('L', 'Baixo'), ('H', 'Alto')]),
    ('A', 'Impacto na disponibilidade:', [('N', 'Nenhum'), ('L', 'Baixo'), ('H', 'Alto')]),
)


def ler_avaliacao():
    print('\n1 - Questionário CVSS Base 3.1\n2 - Colar vetor Base 3.0, 3.1 ou 4.0\n0 - Cancelar')
    opcao = ler_inteiro('Opção: ', minimo=0, maximo=2)
    if opcao == 0:
        return None
    if opcao == 1:
        partes = ['CVSS:3.1']
        print('Avalie as condições da falha. A nota não mede sozinha o risco do ativo.')
        for chave, pergunta, valores in METRICAS:
            print(f'\n{chave} — {pergunta}')
            for indice, (codigo, rotulo) in enumerate(valores, 1):
                print(f'{indice} - {rotulo} ({codigo})')
            indice = ler_inteiro('Opção: ', minimo=1, maximo=len(valores))
            partes.append(f'{chave}:{valores[indice - 1][0]}')
        return calcular_cvss('/'.join(partes))
    while True:
        vetor = ler_texto('Vetor CVSS (Enter cancela): ', obrigatorio=False)
        if not vetor:
            return None
        try:
            return calcular_cvss(vetor)
        except ValueError as erro:
            mensagem_erro(str(erro))


def mostrar_avaliacao(avaliacao):
    print(f'CVSS Base {avaliacao.versao}: {avaliacao.nota:.1f} — {avaliacao.severidade}')
    print(f'Vetor: {avaliacao.vetor}\nFonte: {avaliacao.fonte}')
