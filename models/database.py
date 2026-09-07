# Importando o Flask-SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
# Carregando o SQLAlchemy em uma variável
db = SQLAlchemy()

# Criando uma classe para representar os favoritos no banco
class Favorito(db.Model):
    # Definindo os atributos (colunas) da tabela
    # Schema
    id = db.Column(db.Integer, primary_key=True)
    breed_id = db.Column(db.String(50))
    nome = db.Column(db.String(150))
    origem = db.Column(db.String(150))
    imagem = db.Column(db.String(255))

    # Inicializando as variáveis na classe (método construtor)
    def __init__(self, breed_id, nome, origem, imagem):
        self.breed_id = breed_id
        self.nome = nome
        self.origem = origem
        self.imagem = imagem
