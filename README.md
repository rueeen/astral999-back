# astral999-back

API de Astral999 para usuarios, catálogo de tarot y lecturas personalizadas con Anthropic. Está construida con Django, Django REST Framework y autenticación JWT.

## Requisitos

- Python 3.10 o superior
- SQLite para desarrollo o PostgreSQL mediante `DATABASE_URL`
- Una clave de API de Anthropic para generar lecturas

## Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_cards
python manage.py createsuperuser
python manage.py runserver
```

Completa al menos `SECRET_KEY`, `ANTHROPIC_API_KEY` y `ANTHROPIC_MODEL` en `.env` antes de ejecutar el servidor. Los tests usan el runner de Django:

```bash
python manage.py test
```

## Endpoints

| Método | Ruta | Descripción | Acceso |
| --- | --- | --- | --- |
| POST | `/api/auth/register/` | Registro | Público |
| POST | `/api/auth/login/` | Obtener tokens JWT | Público |
| POST | `/api/auth/refresh/` | Renovar y rotar tokens | Público |
| POST | `/api/auth/logout/` | Invalidar refresh token | Autenticado |
| GET, PUT | `/api/users/me/` | Consultar o actualizar perfil | Autenticado |
| GET | `/api/users/me/quota/` | Consultar plan y cuota | Autenticado |
| GET | `/api/cards/` | Listar cartas | Público |
| GET | `/api/cards/<slug>/` | Detalle de carta | Público |
| GET, POST | `/api/readings/` | Listar o crear lecturas | Autenticado |
| GET | `/api/readings/<id>/` | Detalle propio | Autenticado |
| PATCH | `/api/readings/<id>/favorite/` | Fijar estado favorito | Autenticado |
| GET | `/api/readings/shared/<uuid>/` | Lectura compartida | Público |

## Variables de entorno

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Django; obligatoria en producción. |
| `DEBUG` | Activa el modo desarrollo (`True`/`False`). |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por comas. |
| `DATABASE_URL` | URL de PostgreSQL; vacío usa SQLite. |
| `CORS_ALLOWED_ORIGINS` | Orígenes CORS, separados por comas. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes CSRF confiables, separados por comas. |
| `ANTHROPIC_API_KEY` | Clave de Anthropic. |
| `ANTHROPIC_MODEL` | Identificador del modelo de Anthropic. |
| `ANTHROPIC_TIMEOUT` | Timeout de la llamada a Anthropic en segundos. |
