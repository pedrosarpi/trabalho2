"""Interface web Flask. O domínio e o modelo linear continuam independentes da UI."""
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps
import hmac
import json
import os
import secrets
import threading
import time

from filelock import Timeout
from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, request,
                   Response, session, url_for)

from app.caminhos import arquivo_dados
from app.autenticacao import RepositorioUsuarios
from app.consulta_cve import ClienteNVD, ErroConsultaCVE
from app.dados import ErroArmazenamento
from app.equipamentos import Equipamento, converter_id
from app.interface_cvss import METRICAS
from app.modelos import SeveridadeVulnerabilidade, StatusAtivo, StatusTratamento, TipoAtivo, Vulnerabilidade
from app.riscos import ErroAnaliseRisco
from app.seguranca import calcular_cvss, validar_cve
from app.servicos import ConflitoEdicao, ServicoInventario


class LimiteLogin:
    """Limite local por IP, com memória limitada; implantação usa um worker."""
    def __init__(self):
        self.falhas = defaultdict(deque)
        self.lock = threading.Lock()

    def permitir(self, chave):
        with self.lock:
            agora = time.monotonic()
            for k in list(self.falhas):
                while self.falhas[k] and self.falhas[k][0] < agora - 300:
                    self.falhas[k].popleft()
                if not self.falhas[k]:
                    del self.falhas[k]
            return len(self.falhas.get(chave, ())) < 10

    def falhou(self, chave):
        with self.lock:
            if len(self.falhas) > 10000:
                self.falhas.pop(next(iter(self.falhas)))
            self.falhas[chave].append(time.monotonic())


def criar_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        INVENTARIO_ARQUIVO=os.environ.get('INVENTARIO_ARQUIVO', arquivo_dados('vulnerabilidades.json')),
        USUARIOS_ARQUIVO=os.environ.get('USUARIOS_ARQUIVO', arquivo_dados('usuarios.json')),
        PERMITIR_CADASTRO=os.environ.get('PERMITIR_CADASTRO', 'true').lower() == 'true',
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SEGURO', 'false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8), MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if config:
        app.config.update(config)
    if not app.config['SECRET_KEY'] or len(app.config['SECRET_KEY']) < 32:
        raise RuntimeError('Defina SECRET_KEY com pelo menos 32 caracteres aleatórios (veja README.md).')
    servico = ServicoInventario(app.config['INVENTARIO_ARQUIVO'])
    usuarios = RepositorioUsuarios(app.config['USUARIOS_ARQUIVO'])
    app.extensions.update(inventario=servico, usuarios=usuarios)
    inicio = time.monotonic()
    instancia = secrets.token_hex(8)
    limite = LimiteLogin()
    cliente = ClienteNVD()
    nvd_lock = threading.Lock()
    consultas = {}  # Resultados no servidor; não confiar em nota/descrição enviada pelo navegador.

    def csrf():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    @app.before_request
    def preparar():
        g.usuario = None
        if request.endpoint in ('static', 'saude'):
            return
        if session.get('usuario_id'):
            u = usuarios.obter(session['usuario_id'])
            if u and u['versao'] == session.get('versao'):
                g.usuario = u
            else:
                session.clear()
        if request.method == 'POST':
            token = request.form.get('csrf', '')
            if not token or not hmac.compare_digest(token.encode(), session.get('csrf', '').encode()):
                abort(400, description='Formulário expirado ou inválido. Recarregue a página e tente novamente.')

    @app.after_request
    def cabecalhos(resposta):
        resposta.headers['X-Content-Type-Options'] = 'nosniff'
        resposta.headers['X-Frame-Options'] = 'DENY'
        resposta.headers['Referrer-Policy'] = 'same-origin'
        resposta.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if request.endpoint != 'static':
            resposta.headers['Cache-Control'] = 'no-store'
        return resposta

    def protegido(funcao):
        @wraps(funcao)
        def executar(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for('login'))
            return funcao(*args, **kwargs)
        return executar

    def contexto_inventario():
        inv, revisao = servico.ler()
        return inv, revisao

    def ativo_de(inv, id_ativo):
        ativo = inv.obter(id_ativo)
        if ativo is None:
            abort(404, description='Ativo não encontrado.')
        return ativo

    def vulnerabilidade_de(ativo, indice):
        if not 0 <= indice < len(ativo.vulnerabilidades):
            abort(404, description='Vulnerabilidade não encontrada.')
        return ativo.vulnerabilidades[indice]

    def obrigatorio(chave, maximo=1000):
        valor = request.form.get(chave, '').strip()
        if not valor or len(valor) > maximo:
            raise ValueError(f'Preencha {chave.replace("_", " ")} (até {maximo} caracteres).')
        return valor

    def enumerado(classe, chave):
        try:
            return classe[request.form.get(chave, '')]
        except KeyError:
            raise ValueError(f'Selecione um valor válido para {chave}.') from None

    def carimbar(obj, novo=False):
        if novo:
            obj.adicionado_por = g.usuario['login']
            obj.adicionado_por_id = g.usuario['id']
        obj.ultima_modificacao_por = g.usuario['login']
        obj.ultima_modificacao_por_id = g.usuario['id']

    def analise(inv):
        try:
            return inv.calcular_riscos(), None
        except ErroAnaliseRisco as erro:
            return None, str(erro)

    @app.context_processor
    def comuns():
        return dict(csrf=csrf, tipos=TipoAtivo, status_ativos=StatusAtivo, severidades=SeveridadeVulnerabilidade,
                    tratamentos=StatusTratamento, usuario=g.get('usuario'),
                    cadastro_aberto=app.config['PERMITIR_CADASTRO'])

    @app.template_filter('rotulo')
    def rotulo(valor):
        nomes = {'MEDIA': 'Média', 'CRITICA': 'Crítica', 'NAO_AVALIADA': 'Não avaliada',
                 'SERVICO': 'Serviço', 'EQUIPAMENTO': 'Equipamento', 'SISTEMA': 'Sistema',
                 'BANCO_DE_DADOS': 'Banco de dados', 'DISPOSITIVO_DE_REDE': 'Dispositivo de rede',
                 'EM_MANUTENCAO': 'Em manutenção', 'EM_TRATAMENTO': 'Em tratamento',
                 'ACEITA_COMO_RISCO': 'Aceita como risco'}
        texto = valor.name if hasattr(valor, 'name') else str(valor)
        return nomes.get(texto, texto.replace('_', ' ').capitalize())

    @app.template_filter('numero')
    def numero(valor):
        return f'{float(valor):.2f}'.replace('.', ',') if valor is not None else '—'

    @app.errorhandler(ValueError)
    def entrada_invalida(erro):
        codigo = 409 if isinstance(erro, ConflitoEdicao) else 400
        return render_template('erro.html', codigo=codigo, mensagem=str(erro)), codigo

    @app.errorhandler(ErroArmazenamento)
    @app.errorhandler(Timeout)
    def armazenamento_indisponivel(erro):
        app.logger.error('Armazenamento indisponível: %s', erro)
        return render_template('erro.html', codigo=503,
                               mensagem='Não foi possível acessar os dados. Nenhum arquivo foi substituído. '
                               'O responsável pelo servidor deve conferir os arquivos e permissões.'), 503

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(429)
    def erro_http(erro):
        return render_template('erro.html', codigo=erro.code, mensagem=erro.description), erro.code

    @app.get('/healthz')
    def saude():
        try:
            servico.ler()
            usuarios.listar()
        except (ErroArmazenamento, Timeout, OSError):
            return jsonify(status='erro'), 503
        return jsonify(status='ok', uptime_seconds=round(time.monotonic() - inicio, 3), instancia=instancia,
                       horario_utc=datetime.now(timezone.utc).isoformat())

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if g.usuario:
            return redirect(url_for('painel'))
        if request.method == 'POST':
            ip = request.remote_addr or 'local'
            if not limite.permitir(ip):
                abort(429, description='Muitas tentativas. Aguarde cinco minutos e tente novamente.')
            u = usuarios.autenticar(request.form.get('login', '').strip(), request.form.get('senha', ''))
            if u:
                session.clear()
                session.update(usuario_id=u['id'], versao=u['versao'])
                session.permanent = True
                return redirect(url_for('painel'))
            limite.falhou(ip)
            flash('Usuário ou senha inválidos.', 'erro')
        return render_template('login.html')

    @app.route('/cadastro', methods=['GET', 'POST'])
    def cadastro():
        if not app.config['PERMITIR_CADASTRO']:
            abort(404, description='O cadastro de novas contas está fechado neste servidor.')
        if request.method == 'POST':
            senha = request.form.get('senha', '')
            if senha != request.form.get('confirmacao'):
                raise ValueError('As senhas não coincidem.')
            if not usuarios.registrar(obrigatorio('login', 64), senha):
                raise ValueError('Este login já está em uso.')
            flash('Conta criada. Entre com seu usuário e senha.', 'sucesso')
            return redirect(url_for('login'))
        return render_template('login.html', cadastro=True)

    @app.post('/sair')
    @protegido
    def sair():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @protegido
    def painel():
        inv, rev = contexto_inventario()
        resultado, erro = analise(inv)
        ativos = inv.listar()
        vulns = [v for a in ativos for v in a.vulnerabilidades]
        abertos = sum(v.status in (StatusTratamento.ABERTA, StatusTratamento.EM_TRATAMENTO) for v in vulns)
        ordem = []
        if resultado and resultado.x is not None:
            ordem = sorted(zip(resultado.modelo.equipamentos, resultado.modelo.b, resultado.x),
                           key=lambda item: item[2], reverse=True)
        return render_template('painel.html', ativos=ativos, vulns=vulns, abertos=abertos,
                               resultado=resultado, erro=erro, ordem=ordem, revisao=rev)

    @app.get('/ativos')
    @protegido
    def ativos():
        inv, rev = contexto_inventario()
        termo = request.args.get('q', '').strip()
        lista = inv.buscar(termo) if termo else inv.listar()
        if request.args.get('tipo'):
            lista = [a for a in lista if a.tipo.name == request.args['tipo']]
        return render_template('ativos.html', ativos=lista, revisao=rev, termo=termo)

    @app.route('/ativos/novo', methods=['GET', 'POST'])
    @app.route('/ativos/<int:identificador>/editar', methods=['GET', 'POST'])
    @protegido
    def ativo_form(identificador=None):
        inv, rev = contexto_inventario()
        ativo = ativo_de(inv, identificador) if identificador is not None else None
        contas = usuarios.listar()
        if request.method == 'POST':
            with servico.editar(request.form.get('revisao')) as editavel:
                anterior = ativo_de(editavel, identificador) if identificador is not None else None
                dados = anterior.to_dict() if anterior else {}
                resp_id = request.form.get('responsavel_id', '')
                responsavel = next((u for u in contas if u['id'] == resp_id), None)
                if resp_id and not responsavel:
                    raise ValueError('O responsável selecionado não existe mais. Recarregue a página.')
                dados.update(id_ativo=identificador if anterior else converter_id(request.form.get('id_ativo')),
                             nome=obrigatorio('nome', 120),
                             responsavel=responsavel['login'] if responsavel else obrigatorio('responsavel', 120),
                             responsavel_id=resp_id, setor_localizacao=obrigatorio('setor_localizacao', 160),
                             tipo=enumerado(TipoAtivo, 'tipo').name, status=enumerado(StatusAtivo, 'status').name,
                             descricao=request.form.get('descricao', '').strip()[:5000])
                novo = Equipamento.from_dict(dados)
                carimbar(novo, novo=anterior is None)
                if anterior:
                    editavel.substituir(novo)
                else:
                    editavel.adicionar(novo)
            flash('Ativo salvo.', 'sucesso')
            return redirect(url_for('ativo_detalhe', identificador=novo.id_ativo))
        return render_template('ativo_form.html', ativo=ativo, contas=contas, revisao=rev)

    @app.get('/ativos/<int:identificador>')
    @protegido
    def ativo_detalhe(identificador):
        inv, rev = contexto_inventario()
        ativo = ativo_de(inv, identificador)
        contas = {u['id']: u['login'] for u in usuarios.listar()}
        return render_template('ativo.html', ativo=ativo, revisao=rev, contas=contas, inv=inv)

    @app.post('/ativos/<int:identificador>/excluir')
    @protegido
    def ativo_excluir(identificador):
        with servico.editar(request.form.get('revisao')) as inv:
            ativo_de(inv, identificador)
            inv.remover(identificador)
        flash('Ativo removido, incluindo suas vulnerabilidades e dependências relacionadas.', 'sucesso')
        return redirect(url_for('ativos'))

    @app.get('/vulnerabilidades')
    @protegido
    def vulnerabilidades():
        inv, rev = contexto_inventario()
        lista = [(a, i, v) for a in inv.listar() for i, v in enumerate(a.vulnerabilidades)]
        termo = request.args.get('q', '').casefold()
        lista = [item for item in lista if termo in ' '.join((item[0].nome, item[2].descricao,
                                                              item[2].cve_id or '')).casefold()]
        if request.args.get('status'):
            lista = [item for item in lista if item[2].status.name == request.args['status']]
        return render_template('vulnerabilidades.html', lista=lista, ativos=inv.listar(), revisao=rev)

    @app.route('/ativos/<int:identificador>/vulnerabilidades/nova', methods=['GET', 'POST'])
    @app.route('/ativos/<int:identificador>/vulnerabilidades/<int:indice>/editar', methods=['GET', 'POST'])
    @protegido
    def vuln_form(identificador, indice=None):
        inv, rev = contexto_inventario()
        ativo = ativo_de(inv, identificador)
        vuln = vulnerabilidade_de(ativo, indice) if indice is not None else None
        if request.method == 'POST':
            with servico.editar(request.form.get('revisao')) as inv_editavel:
                a = ativo_de(inv_editavel, identificador)
                anterior = vulnerabilidade_de(a, indice) if indice is not None else None
                vetor = request.form.get('vetor', '').strip()
                cve_id = validar_cve(request.form.get('cve_id', ''))
                # A fonte consultada só vale para o mesmo CVE e o mesmo vetor.
                mesma_origem = (anterior and anterior.cve_id == cve_id and anterior.cvss
                                and anterior.cvss.vetor == vetor)
                cvss = anterior.cvss if mesma_origem else (
                    calcular_cvss(vetor) if vetor else None)
                v = Vulnerabilidade(obrigatorio('descricao', 10000), obrigatorio('categoria', 160),
                                    enumerado(SeveridadeVulnerabilidade, 'severidade'),
                                    enumerado(StatusTratamento, 'status'),
                                    cve_id=cve_id, cvss=cvss,
                                    consultado_em=(anterior.consultado_em if anterior and
                                                   anterior.cve_id == cve_id else None))
                if anterior:
                    v.adicionado_por = anterior.adicionado_por
                    v.adicionado_por_id = anterior.adicionado_por_id
                carimbar(v, novo=anterior is None)
                if v.cve_id and any(outro is not anterior and outro.cve_id == v.cve_id for outro in a.vulnerabilidades):
                    raise ValueError('Este CVE já está cadastrado neste ativo.')
                if anterior:
                    # Substitui na mesma posição; a revisão protege formulários antigos.
                    a.substituir_vulnerabilidade(indice, v)
                else:
                    a.adicionar_vulnerabilidade(v)
                carimbar(a)
            flash('Vulnerabilidade salva.', 'sucesso')
            return redirect(url_for('ativo_detalhe', identificador=identificador))
        return render_template('vuln_form.html', ativo=ativo, vuln=vuln, revisao=rev)

    @app.post('/ativos/<int:identificador>/vulnerabilidades/<int:indice>/excluir')
    @protegido
    def vuln_excluir(identificador, indice):
        with servico.editar(request.form.get('revisao')) as inv:
            a = ativo_de(inv, identificador)
            a.remover_vulnerabilidade(vulnerabilidade_de(a, indice))
            carimbar(a)
        flash('Vulnerabilidade removida.', 'sucesso')
        return redirect(url_for('ativo_detalhe', identificador=identificador))

    @app.route('/cvss', methods=['GET', 'POST'])
    @protegido
    def cvss():
        inv, rev = contexto_inventario()
        resultado = None
        if request.method == 'POST':
            vetor = request.form.get('vetor', '')
            if request.form.get('modo') == 'questionario':
                vetor = 'CVSS:3.1/' + '/'.join(f'{chave}:{request.form.get(chave, "")}' for chave, _, _ in METRICAS)
            resultado = calcular_cvss(vetor)
            if request.form.get('acao') == 'aplicar':
                try:
                    id_texto, indice_texto = request.form.get('alvo', '').split(':')
                    identificador, indice = converter_id(id_texto), int(indice_texto)
                except (ValueError, TypeError):
                    raise ValueError('Selecione uma vulnerabilidade.') from None
                with servico.editar(request.form.get('revisao')) as editavel:
                    a = ativo_de(editavel, identificador)
                    v = vulnerabilidade_de(a, indice)
                    if v.cvss and request.form.get('confirmar_substituicao') != 'sim':
                        raise ValueError('Confirme a substituição do CVSS existente.')
                    cve = validar_cve(request.form.get('cve_id', '')) or v.cve_id
                    if cve and any(outro is not v and outro.cve_id == cve for outro in a.vulnerabilidades):
                        raise ValueError('Este CVE já está cadastrado neste ativo.')
                    if cve != v.cve_id:
                        v.consultado_em = None
                    v.cvss, v.cve_id = resultado, cve
                    carimbar(v)
                    carimbar(a)
                flash('CVSS aplicado. A severidade foi atualizada automaticamente.', 'sucesso')
                return redirect(url_for('ativo_detalhe', identificador=identificador))
        return render_template('cvss.html', resultado=resultado, metricas=METRICAS,
                               ativos=inv.listar(), revisao=rev)

    @app.route('/cve', methods=['GET', 'POST'])
    @protegido
    def cve():
        inv, rev = contexto_inventario()
        resultado = None
        token = None
        if request.method == 'POST':
            if request.form.get('acao') == 'importar':
                token = request.form.get('consulta', '')
                with nvd_lock:
                    consulta = consultas.get(token)
                if not consulta or consulta[0] != g.usuario['id'] or time.monotonic() - consulta[1] > 900:
                    raise ValueError('A consulta expirou. Consulte novamente antes de importar.')
                resultado = consulta[2]
                indice = request.form.get('avaliacao', '')
                avaliacao = None
                if resultado.avaliacoes:
                    try:
                        numero = int(indice)
                        if not 0 <= numero < len(resultado.avaliacoes):
                            raise ValueError()
                        avaliacao = resultado.avaliacoes[numero]
                    except (ValueError, IndexError):
                        raise ValueError('Selecione a avaliação CVSS que deseja importar.') from None
                with servico.editar(request.form.get('revisao')) as editavel:
                    a = ativo_de(editavel, converter_id(request.form.get('ativo')))
                    v = Vulnerabilidade(resultado.descricao, obrigatorio('categoria', 160),
                                        SeveridadeVulnerabilidade.NAO_AVALIADA,
                                        enumerado(StatusTratamento, 'status'), cve_id=resultado.cve_id,
                                        cvss=avaliacao, consultado_em=resultado.consultado_em)
                    carimbar(v, novo=True)
                    a.adicionar_vulnerabilidade(v)
                    carimbar(a)
                flash('CVE importado com fonte, data e autoria.', 'sucesso')
                return redirect(url_for('ativo_detalhe', identificador=a.id_ativo))
            try:
                with nvd_lock:
                    resultado = cliente.consultar(request.form.get('cve_id', ''))
                    token = secrets.token_urlsafe(24)
                    for chave in list(consultas):
                        if time.monotonic() - consultas[chave][1] > 900:
                            del consultas[chave]
                    if len(consultas) >= 100:
                        consultas.pop(next(iter(consultas)))
                    consultas[token] = (g.usuario['id'], time.monotonic(), resultado)
            except ErroConsultaCVE as erro:
                flash(str(erro) + ' O cadastro manual e a calculadora continuam disponíveis.', 'erro')
        return render_template('cve.html', resultado=resultado, consulta=token, ativos=inv.listar(), revisao=rev)

    @app.route('/dependencias', methods=['GET', 'POST'])
    @protegido
    def dependencias():
        if request.method == 'POST':
            with servico.editar(request.form.get('revisao')) as inv:
                destino = converter_id(request.form.get('destino'))
                origem = converter_id(request.form.get('origem'))
                if request.form.get('acao') == 'excluir':
                    inv.remover_dependencia(destino, origem)
                else:
                    try:
                        peso = float(request.form.get('peso', '').replace(',', '.'))
                    except ValueError:
                        raise ValueError('Informe um peso numérico, por exemplo 0,25.') from None
                    inv.definir_dependencia(destino, origem, peso)
                carimbar(ativo_de(inv, destino))
            flash('Dependências atualizadas.', 'sucesso')
            return redirect(url_for('dependencias'))
        inv, rev = contexto_inventario()
        return render_template('dependencias.html', ativos=inv.listar(), inv=inv, revisao=rev)

    @app.get('/riscos')
    @protegido
    def riscos():
        inv, rev = contexto_inventario()
        resultado, erro = analise(inv)
        return render_template('riscos.html', resultado=resultado, erro=erro, revisao=rev)

    @app.get('/exportar')
    @protegido
    def exportar():
        inv, _ = contexto_inventario()
        return Response(json.dumps([a.to_dict() for a in inv.listar()], ensure_ascii=False, indent=2),
                        mimetype='application/json',
                        headers={'Content-Disposition': 'attachment; filename=inventario.json'})

    @app.route('/usuarios', methods=['GET', 'POST'])
    @protegido
    def contas():
        if request.method == 'POST':
            atual = usuarios.autenticar(g.usuario['login'], request.form.get('senha_atual', ''))
            if not atual:
                raise ValueError('A senha atual está incorreta.')
            acao = request.form.get('acao')
            if acao == 'renomear':
                if not usuarios.renomear(atual['login'], obrigatorio('novo_login', 64)):
                    raise ValueError('Este login já está em uso.')
                flash('Login alterado. Os vínculos por ID foram preservados.', 'sucesso')
            elif acao == 'senha':
                senha = request.form.get('nova_senha', '')
                if senha != request.form.get('confirmacao'):
                    raise ValueError('As senhas não coincidem.')
                usuarios.alterar_senha(atual['login'], senha)
                session.clear()
                flash('Senha alterada. Entre novamente; as sessões anteriores foram encerradas.', 'sucesso')
                return redirect(url_for('login'))
            elif acao == 'excluir':
                if request.form.get('confirmacao_exclusao') != atual['login']:
                    raise ValueError('Digite seu login para confirmar a exclusão.')
                usuarios.deletar(atual['login'])
                session.clear()
                flash('Conta excluída. O histórico do inventário foi preservado.', 'sucesso')
                return redirect(url_for('login'))
            else:
                raise ValueError('Ação de conta inválida.')
            return redirect(url_for('contas'))
        inv, _ = contexto_inventario()
        lista = usuarios.listar()
        for u in lista:
            u['ativos'] = sum(a.responsavel_id == u['id'] for a in inv.listar())
        return render_template('usuarios.html', contas=lista)

    return app


if __name__ == '__main__':
    criar_app().run(host='127.0.0.1', port=8000, debug=False)
