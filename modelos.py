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

class Equipamentos:
    def __init__(self, id_ativo, nome, responsavel, setor_localizacao, tipo, status, descricao, vulnerabilidades=None):
        self.id_ativo = id_ativo
        self.nome = nome
        self.responsavel = responsavel
        self.setor_localizacao = setor_localizacao
        self.tipo = tipo
        self.status = status
        self.descricao = descricao
        self.vulnerabilidades = vulnerabilidades if vulnerabilidades is not None else []

    def to_dict(self):
        return {
            "id_ativo": self.id_ativo,
            "nome": self.nome,
            "responsavel": self.responsavel,
            "setor_localizacao": self.setor_localizacao,
            "tipo": self.tipo,
            "status": self.status,
            "descricao": self.descricao,
            "vulnerabilidades": self.vulnerabilidades
        }