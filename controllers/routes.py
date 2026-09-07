import csv
import io
import random
import re

import requests
from flask import Response, jsonify, render_template, request, redirect, url_for, flash, session
from flask_caching import Cache

from models.database import db, Favorito

API_URL = 'https://api.thecatapi.com/v1/breeds'
API_SEARCH_URL = 'https://api.thecatapi.com/v1/breeds/search'
FALLBACK_API_URL = 'https://unpkg.com/cat-breeds@1.2.0/cat-breeds.json'
API_HEADERS = {'User-Agent': 'catalogo-gatos/1.0'}
cache = Cache()


@cache.memoize(timeout=300)
def buscar_racas():
    """Busca raças na API principal ou usa uma fonte pública alternativa."""
    try:
        resposta = requests.get(API_URL, headers=API_HEADERS, timeout=10)
        resposta.raise_for_status()
        return resposta.json()
    except requests.RequestException:
        resposta = requests.get(FALLBACK_API_URL, headers=API_HEADERS, timeout=15)
        resposta.raise_for_status()
        return normalizar_racas_alternativas(resposta.json())


def normalizar_racas_alternativas(registros):
    """Converte registros da fonte alternativa para o formato usado pelos templates."""
    racas = []
    for registro in registros:
        nome = registro.get('breed', 'Raça de gato').replace('\n', ' ').strip()
        identificador = re.sub(r'[^a-z0-9]+', '-', nome.lower()).strip('-')
        origem = registro.get('origin', 'Origem não informada').replace('\n', ' ').strip()
        imagem = imagem_em_alta_resolucao(registro.get('image'))
        racas.append({
            'id': identificador,
            'name': nome,
            'origin': origem,
            'temperament': registro.get('type', 'Não informado'),
            'life_span': 'Não informada',
            'description': f"Pelagem: {registro.get('coat', 'não informada')}. Padrão: {registro.get('pattern', 'não informado')}.",
            'image': {'url': imagem} if imagem else None,
            'wikipedia_url': '',
        })
    return racas


def imagem_em_alta_resolucao(url):
    """Remove o sufixo de miniatura do Wikimedia quando a fonte fornece um original."""
    if not url:
        return None
    marcador = '/commons/thumb/'
    if marcador in url:
        base, caminho = url.split(marcador, 1)
        partes = caminho.split('/')
        if len(partes) >= 4:
            return f"{base}/commons/{'/'.join(partes[:-1])}"
    return url


def buscar_por_nome(nome):
    """Consulta o endpoint de busca da TheCatAPI para uma raça específica."""
    try:
        resposta = requests.get(API_SEARCH_URL, params={'q': nome}, headers=API_HEADERS, timeout=10)
        resposta.raise_for_status()
        return resposta.json()
    except requests.RequestException:
        termo = nome.lower()
        return [raca for raca in buscar_racas() if termo in raca.get('name', '').lower()]


def filtrar_racas(lista_racas, origem='', temperamento='', busca=''):
    """Filtra uma lista de raças por origem, temperamento e nome."""
    origem, temperamento, busca = origem.strip().lower(), temperamento.strip().lower(), busca.strip().lower()
    return [raca for raca in lista_racas if (
        (not origem or raca.get('origin', '').strip().lower() == origem)
        and (not temperamento or temperamento in raca.get('temperament', '').lower())
        and (not busca or busca in raca.get('name', '').lower())
    )]


def opcoes_filtro(lista_racas):
    """Retorna opções únicas e ordenadas para os filtros do catálogo."""
    origens = sorted({r.get('origin', '').strip() for r in lista_racas if r.get('origin')})
    temperamentos = sorted({p.strip() for r in lista_racas for p in r.get('temperament', '').split(',') if p.strip()})
    return origens, temperamentos


def init_app(app):
    """Registra cache, contexto global e todas as rotas da aplicação."""
    cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})

    @app.context_processor
    def dados_globais():
        """Disponibiliza a contagem de favoritos em todos os templates."""
        try:
            favoritos_count = Favorito.query.count()
        except Exception:
            favoritos_count = 0
        return {'favoritos_count': favoritos_count}

    @app.route('/')
    @app.route('/animals')
    def animals():
        """Exibe o catálogo filtrado e ordenado."""
        origem, temperamento = request.args.get('origem', ''), request.args.get('temperamento', '')
        busca, ordenacao = request.args.get('busca', ''), request.args.get('ordenacao', 'az')
        try:
            todas_racas = buscar_racas()
            lista_racas = filtrar_racas(todas_racas, origem, temperamento, busca)
            if ordenacao == 'vida':
                lista_racas.sort(key=lambda r: int(r.get('life_span', '0').split('-')[0].strip() or 0))
            else:
                lista_racas.sort(key=lambda r: r.get('name', '').lower(), reverse=ordenacao == 'za')
            origens, temperamentos, erro_api = opcoes_filtro(todas_racas)[0], opcoes_filtro(todas_racas)[1], None
        except requests.RequestException:
            todas_racas, lista_racas, origens, temperamentos = [], [], [], []
            erro_api = 'Não foi possível atualizar os dados agora. As informações disponíveis continuam visíveis.'
        return render_template('animals.html', listaRacas=lista_racas, todasRacas=todas_racas, totalRacas=len(todas_racas), origens=origens,
                               temperamentos=temperamentos, origem_selecionada=origem, temperamento_selecionado=temperamento,
                               busca=busca, ordenacao=ordenacao, erro_api=erro_api)

    @app.route('/animals/<id>')
    def animal_info(id):
        """Exibe os detalhes de uma raça identificada pelo seu ID."""
        try:
            raca_info = next((r for r in buscar_racas() if r.get('id') == id), None)
        except requests.RequestException:
            return render_template('animalinfo.html', racaInfo=None, erro_api='Não foi possível atualizar os detalhes agora.'), 502
        if raca_info is None:
            return render_template('animalinfo.html', racaInfo=None, erro_api=None), 404
        return render_template('animalinfo.html', racaInfo=raca_info, erro_api=None)

    @app.route('/surpresa')
    def surpresa():
        """Redireciona para uma raça aleatória do catálogo."""
        try:
            racas = buscar_racas()
            if racas:
                return redirect(url_for('animal_info', id=random.choice(racas)['id']))
        except requests.RequestException:
            pass
        return redirect(url_for('animals'))

    @app.route('/api/search')
    def api_search():
        """Busca raças diretamente no endpoint de pesquisa da TheCatAPI."""
        nome = request.args.get('q', '').strip()
        if not nome:
            return jsonify([])
        try:
            return jsonify(buscar_por_nome(nome))
        except requests.RequestException:
            return jsonify({'error': 'A busca externa está indisponível.'}), 502

    @app.route('/compare')
    def compare():
        """Compara duas raças lado a lado a partir dos IDs informados."""
        ids = [request.args.get('a', ''), request.args.get('b', '')]
        try:
            todas_racas = buscar_racas()
            racas = [r for r in todas_racas if r.get('id') in ids]
        except requests.RequestException:
            todas_racas, racas = [], []
        return render_template('compare.html', racas=racas, todas_racas=todas_racas)

    @app.route('/favoritos', methods=['GET', 'POST'])
    def favoritos():
        """Lista favoritos ou grava uma raça, evitando duplicidade."""
        if request.method == 'POST':
            dados, breed_id = request.form, request.form.get('breed_id', '')
            ajax = request.form.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if Favorito.query.filter_by(breed_id=breed_id).first() is not None:
                if ajax:
                    return jsonify({'ok': False, 'message': 'Essa raça já está nos seus favoritos.', 'count': Favorito.query.count()}), 409
                flash('Essa raça já está nos seus favoritos.', 'info')
                destino = request.form.get('next', '')
                return redirect(destino if destino.startswith('/') else url_for('favoritos'))
            novo_favorito = Favorito(breed_id=breed_id, nome=dados.get('nome', 'Raça sem nome'), origem=dados.get('origem', 'Origem não informada'), imagem=dados.get('imagem', ''))
            db.session.add(novo_favorito)
            db.session.commit()
            session['last_favorite_id'] = novo_favorito.id
            if ajax:
                return jsonify({'ok': True, 'message': 'Raça adicionada aos favoritos.', 'count': Favorito.query.count()})
            flash('Raça adicionada aos favoritos.', 'success')
            destino = request.form.get('next', '')
            return redirect(destino if destino.startswith('/') else url_for('favoritos'))
        return render_template('favoritos.html', listaFavoritos=Favorito.query.order_by(Favorito.id.desc()).all())

    @app.route('/favoritos/undo', methods=['POST'])
    def undoFavorito():
        """Desfaz a inclusão mais recente de favorito durante a sessão atual."""
        favorito_id = session.pop('last_favorite_id', None)
        if favorito_id is not None:
            favorito = db.session.get(Favorito, favorito_id)
            if favorito is not None:
                db.session.delete(favorito)
                db.session.commit()
                flash('A inclusão do favorito foi desfeita.', 'info')
        return redirect(url_for('favoritos'))

    @app.route('/favoritos/export.csv')
    def export_favoritos():
        """Exporta os favoritos atuais em um arquivo CSV UTF-8."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'raça', 'origem', 'imagem'])
        for favorito in Favorito.query.order_by(Favorito.nome).all():
            writer.writerow([favorito.breed_id, favorito.nome, favorito.origem, favorito.imagem])
        return Response('\ufeff' + output.getvalue(), mimetype='text/csv; charset=utf-8', headers={'Content-Disposition': 'attachment; filename=favoritos-gatos.csv'})

    @app.route('/favoritos/delete/<int:id>', methods=['POST'])
    def deleteFavorito(id):
        """Remove um favorito e retorna à coleção."""
        favorito = db.session.get(Favorito, id)
        if favorito is not None:
            db.session.delete(favorito)
            db.session.commit()
            flash('Favorito removido.', 'success')
        return redirect(url_for('favoritos'))

    @app.route('/estatisticas')
    def estatisticas():
        """Calcula os dados usados pelo dashboard visual do catálogo."""
        racas = buscar_racas()
        origens = {}
        faixas = {}
        temperamentos = {}
        for raca in racas:
            origem = raca.get('origin', 'Não informada').split(',')[0].strip() or 'Não informada'
            origens[origem] = origens.get(origem, 0) + 1
            vida = raca.get('life_span', '')
            inicio = vida.split('-')[0].strip()
            faixa = f'{inicio} anos' if inicio.isdigit() else 'Não informado'
            faixas[faixa] = faixas.get(faixa, 0) + 1
            for temperamento in raca.get('temperament', '').split(','):
                nome = temperamento.strip()
                if nome:
                    temperamentos[nome] = temperamentos.get(nome, 0) + 1
        return render_template('estatisticas.html', total=len(racas), origens=dict(sorted(origens.items(), key=lambda item: item[1], reverse=True)[:12]), faixas=faixas, temperamentos=dict(sorted(temperamentos.items(), key=lambda item: item[1], reverse=True)[:12]))

    @app.route('/mapa')
    def mapa():
        """Exibe origens aproximadas das raças em um mapa interativo."""
        coordenadas = {
            'United States': (38, -97), 'United Kingdom': (54, -3), 'England': (54, -3),
            'France': (46, 2), 'Germany': (51, 10), 'Brazil': (-10, -52), 'Egypt': (27, 30),
            'China': (35, 103), 'Russia': (61, 90), 'Japan': (36, 138), 'Australia': (-25, 134),
            'Thailand': (15, 101), 'Turkey': (39, 35), 'Canada': (57, -106), 'Greece': (39, 22),
            'Cyprus': (35, 33), 'Norway': (62, 10), 'Sweden': (62, 15), 'Italy': (42, 12),
        }
        marcadores = []
        for raca in buscar_racas():
            origem = raca.get('origin', 'Não informada')
            ponto = next((valor for chave, valor in coordenadas.items() if chave.lower() in origem.lower()), None)
            if ponto:
                marcadores.append({'id': raca['id'], 'name': raca.get('name', 'Raça'), 'origin': origem, 'lat': ponto[0], 'lng': ponto[1]})
        return render_template('mapa.html', marcadores=marcadores)

    @app.route('/galeria')
    def galeria():
        """Exibe uma galeria visual de todas as raças que possuem imagem."""
        racas = [raca for raca in buscar_racas() if raca.get('image') and raca['image'].get('url')]
        return render_template('galeria.html', racas=racas)

    return app
