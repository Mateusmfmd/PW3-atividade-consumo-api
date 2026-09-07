import pymysql
import pymysql.cursors
from flask import Flask
from models.database import db
from controllers import routes

# Configuração usada na aula: MySQL local com root sem senha.
DB_NAME = 'catalogo_gatos'
DB_USER = 'root'
DB_PASSWORD = ''
DB_HOST = 'localhost'
DB_PORT = 3306
SECRET_KEY = 'catalogo-gatos-chave-secreta'

app = Flask(__name__, template_folder='views', static_folder='static')
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DATABASE_NAME'] = DB_NAME
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
routes.init_app(app)


def criar_banco_se_necessario():
    """Cria o banco catalogo_gatos caso ele ainda não exista."""
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}` '
                'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
            )
        connection.commit()
    finally:
        connection.close()


if __name__ == '__main__':
    try:
        criar_banco_se_necessario()
        with app.app_context():
            db.create_all()
        print(f'Banco {DB_NAME} conectado. Servidor em http://localhost:5000')
        app.run(port=5000, debug=True)
    except pymysql.err.OperationalError as erro:
        codigo = erro.args[0] if erro.args else None
        if codigo == 2003:
            print('ERRO: o MySQL está desligado. Abra o serviço MySQL e execute novamente.')
        elif codigo == 1045:
            print('ERRO: o usuário root deste MySQL possui senha, mas este projeto espera root sem senha.')
        else:
            print(f'ERRO ao conectar ao MySQL: {erro}')
