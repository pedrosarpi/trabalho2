from enum import Enum

class TipoAtivo(Enum):
    EQUIPAMENTO = 1
    SISTEMA = 2
    SERVICO = 3
    DISPOSITIVO_DE_REDE = 4
    BANCO_DE_DADOS = 5

class StatusAtivo(Enum):
    ATIVO = 1
    INATIVO = 2
    EM_MANUTENCAO = 3

class SeveridadeVulnerabilidade(Enum):
    BAIXA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4

class StatusTratamento(Enum):
    ABERTA = 1
    EM_TRATAMENTO = 2
    CORRIGIDA = 3
    ACEITA_COMO_RISCO = 4