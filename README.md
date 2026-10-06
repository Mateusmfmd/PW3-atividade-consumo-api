# Catálogo de animais — Flask

Aplicação web em Flask que consome uma API de raças de animais e oferece busca, filtros, comparação, favoritos, estatísticas, mapa, galeria e exportação CSV.

## Tecnologias

- Python e Flask
- Arquitetura com `controllers`, `models`, `views` e arquivos estáticos
- Testes automatizados com o cliente de testes do Flask

## Execução local

```bash
git clone https://github.com/Mateusmfmd/PW3-atividade-consumo-api.git
cd PW3-atividade-consumo-api
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
python app.py
```

No Windows, ative o ambiente com `.venv\\Scripts\\activate` ou use `executar.bat`.

## Testes

```bash
pytest -q test_app.py
```

## Rotas principais

- `/animals`: catálogo, busca e filtros
- `/animals/<id>`: detalhes de uma raça
- `/compare?a=<id>&b=<id>`: comparação
- `/favoritos`: gerenciamento de favoritos
- `/favoritos/export.csv`: exportação
- `/api/search?q=<termo>`: busca em formato JSON
