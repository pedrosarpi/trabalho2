import json
from collections import deque

class Vulnerabilidade:
    def __init__(self, nome, nivel_risco):
        self.nome = nome
        self.nivel_risco = nivel_risco

    def detalhar(self):
        return f"Vulnerabilidade: {self.nome}, Nível de Risco: {self.nivel_risco}"

    def to_dict(self):
        return {
            "tipo": "base",
            "nome": self.nome,
            "nivel_risco": self.nivel_risco
        }
class VulnerabilidadeRede(Vulnerabilidade):
    def __init__(self, nome, nivel_risco, porta_afetada):
        super().__init__(nome, nivel_risco)
        self.porta_afetada = porta_afetada

    def detalhar(self):
        return f"{super().detalhar()}, Porta Afetada: {self.porta_afetada}"
    
    def to_dict(self):
        dados = super().to_dict()
        dados["tipo"] = "rede"
        dados["porta_afetada"] = self.porta_afetada
        return dados
class VulnerabilidadeSoftware(Vulnerabilidade):
    def __init__(self, nome, nivel_risco, versao_falha):
        super().__init__(nome, nivel_risco)
        self.versao_falha = versao_falha

    def detalhar(self):
        return f"{super().detalhar()}, Versão com Falha: {self.versao_falha}"

    def to_dict(self):
        dados = super().to_dict()
        dados["tipo"] = "software"
        dados["versao_falha"] = self.versao_falha
        return dados    

falha_sql = VulnerabilidadeSoftware("Falha SQL Injection", "Alta", "1.0.0")
falha_roteador = VulnerabilidadeRede("Falha de Configuração do Roteador", "Média", 23)
falha_xss = VulnerabilidadeSoftware("Falha XSS", "Alta", "2.1.3")   

fila_vulnerabilidades = deque()
fila_vulnerabilidades.append(falha_sql)
fila_vulnerabilidades.append(falha_roteador)
fila_vulnerabilidades.append(falha_xss)

dados_salvar = []

for vulnerabilidade in fila_vulnerabilidades:
    dados_salvar.append(vulnerabilidade.to_dict())

nome_arquivo = "vulnerabilidades.json"
with open(nome_arquivo, "w") as arquivo:
    json.dump(dados_salvar, arquivo, indent=4, ensure_ascii=False)
print(f"Dados salvos no arquivo {nome_arquivo}.")

while fila_vulnerabilidades:
    vulnerabilidade = fila_vulnerabilidades.popleft()
    print(vulnerabilidade.detalhar())