from controllers import routes
from app import app

FAKE_BREEDS = [
    {'id': 'test', 'name': 'Gato Teste', 'origin': 'Brasil', 'temperament': 'Calm, Friendly', 'life_span': '12 - 16', 'image': {'url': 'https://example.com/cat.jpg'}},
    {'id': 'no-image', 'name': 'Gato Sem Imagem', 'origin': 'Mundo', 'temperament': 'Active', 'life_span': '10 - 14'},
]

routes.buscar_racas = lambda: FAKE_BREEDS
routes.buscar_por_nome = lambda nome: [FAKE_BREEDS[0]] if 'teste' in nome.lower() else []
client = app.test_client()

response = client.get('/animals')
assert response.status_code == 200
assert b'Gato Teste' in response.data
assert b'image-fallback' in response.data
assert b'Sem imagem' not in response.data

response = client.get('/animals?busca=teste')
assert response.status_code == 200
assert b'Gato Teste' in response.data
assert b'Gato Sem Imagem' not in response.data

response = client.get('/animals?temperamento=friendly')
assert response.status_code == 200
assert b'Gato Teste' in response.data
assert b'Gato Sem Imagem' not in response.data

response = client.get('/animals/no-image')
assert response.status_code == 200
assert b'Gato Sem Imagem' in response.data
assert b'image-fallback visible' in response.data

response = client.get('/animals/inexistente')
assert response.status_code == 404

response = client.get('/api/search?q=teste')
assert response.status_code == 200
assert response.json[0]['id'] == 'test'

response = client.get('/compare?a=test&b=no-image')
assert response.status_code == 200
assert b'Gato Teste' in response.data
assert b'Gato Sem Imagem' in response.data

for pagina in ['/estatisticas', '/mapa', '/galeria']:
    response = client.get(pagina)
    assert response.status_code == 200, pagina

assert len(routes.filtrar_racas(FAKE_BREEDS, busca='maine')) == 0
assert len(routes.filtrar_racas(FAKE_BREEDS, temperamento='friendly')) == 1
assert routes.opcoes_filtro(FAKE_BREEDS)[0] == ['Brasil', 'Mundo']
fallback = routes.normalizar_racas_alternativas([{'breed': 'Gato\nAlternativo', 'origin': 'Brasil', 'image': 'https://example.com/cat.jpg'}])
assert fallback[0]['id'] == 'gato-alternativo'
assert fallback[0]['image']['url'].endswith('cat.jpg')
assert routes.imagem_em_alta_resolucao('https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/gato.jpg/120px-gato.jpg').endswith('/commons/a/ab/gato.jpg')

print('OK catálogo, busca, filtros, API search, comparação e cache')


class FakeQuery:
    def __init__(self, items=None):
        self.items = items or []

    def count(self):
        return len(self.items)

    def filter_by(self, **_kwargs):
        return FakeQuery([])

    def first(self):
        return self.items[0] if self.items else None

    def order_by(self, *_args):
        return self

    def all(self):
        return self.items


class FakeSession:
    def __init__(self):
        self.added = []
        self.deleted = []

    def add(self, item):
        self.added.append(item)

    def commit(self):
        pass

    def get(self, _model, _id):
        return object()

    def delete(self, item):
        self.deleted.append(item)


from unittest.mock import patch

fake_session = FakeSession()
with app.app_context(), patch.object(routes.Favorito, 'query', FakeQuery([]), create=True), patch.object(routes.db, 'session', fake_session):
    response = client.post('/favoritos', data={'breed_id': 'test', 'nome': 'Gato Teste', 'origem': 'Brasil', 'imagem': ''})
    assert response.status_code == 302
    assert len(fake_session.added) == 1
    response = client.get('/favoritos/export.csv')
    assert response.status_code == 200
    assert 'text/csv' in response.content_type
    response = client.post('/favoritos/delete/1')
    assert response.status_code == 302
    assert len(fake_session.deleted) == 1

print('OK POST, exportação CSV e remoção de favoritos')
