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
| `ANTHROPIC_MODEL` | Identificador del modelo de Anthropic (por ejemplo, `claude-sonnet-4-5-20250929`). |
| `ANTHROPIC_TIMEOUT` | Timeout de la llamada a Anthropic en segundos. |
| `ANTHROPIC_TEMPERATURE` | Temperatura opcional. Si no se define, Anthropic usa su valor predeterminado `1.0`. Los modelos de generación 5 rechazan valores distintos del predeterminado, por lo que conviene omitirla al usarlos. |


## Elección del modelo de Anthropic

El modelo se elige mediante `ANTHROPIC_MODEL`. Antes de desplegar, compara estas tres
características en la documentación vigente de Anthropic:

- **Costo por lectura:** una lectura consume los tokens del prompt (pregunta, cartas y
  contexto) y hasta 1200 tokens de salida. Un modelo más capaz suele aumentar el costo;
  estima el importe con los precios de entrada y salida del modelo elegido.
- **Latencia:** los modelos pequeños suelen responder antes, mientras que los modelos con
  razonamiento o pensamiento adaptativo pueden tardar más y consumir parte del presupuesto
  de salida. Prueba el modelo con tiradas de uno, tres y diez naipes.
- **Compatibilidad con `temperature`:** la aplicación solo envía este parámetro cuando
  `ANTHROPIC_TEMPERATURE` está definido explícitamente. Su valor predeterminado es `1.0`.
  Los modelos de generación 5 producen un error 400 si reciben un valor diferente del
  predeterminado; con ellos, deja la variable sin definir (comentada en `.env`).

Tras cambiar de modelo, ejecuta algunas lecturas de prueba para comprobar el tono, el tiempo
hasta la respuesta y que el texto termine completo antes de habilitarlo en producción.

## Historial de lecturas fallidas

`GET /api/readings/` oculta por defecto las lecturas cuya generación falló. Para incluirlas
en el historial administrativo o durante un diagnóstico, usa
`GET /api/readings/?include_failed=true`. El detalle autenticado por id continúa disponible.
