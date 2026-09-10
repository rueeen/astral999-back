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
| POST, PUT | `/api/readings/<id>/feedback/` | Crear o reemplazar el voto propio | Autenticado |
| GET | `/api/readings/<id>/feedback/summary/` | Resumen agregado de feedback | Autenticado |
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
| `ANTHROPIC_PROXY` | Proxy HTTPS opcional; en PythonAnywhere gratuito usa `http://proxy.server:3128`. |
| `ANTHROPIC_TEMPERATURE` | Temperatura opcional. Si no se define, Anthropic usa su valor predeterminado `1.0`. Los modelos de generación 5 rechazan valores distintos del predeterminado, por lo que conviene omitirla al usarlos. |
| `FEEDBACK_FEW_SHOT_EXAMPLES` | Referencias positivas inyectadas por generación (`0` desactiva; máximo efectivo `3`). |
| `MONTHLY_BUDGET` | Presupuesto mensual de generación, en la moneda de los precios cargados. `0` lo desactiva. |
| `TRIAL_MODE` | Activa (`True`) la concesión temporal del plan premium. Por defecto es `False`. |
| `TRIAL_ENDS_AT` | Fecha/hora ISO de vencimiento obligatoria cuando `TRIAL_MODE=True`. |

### Modo de prueba premium y advertencia de costos

Con `TRIAL_MODE=True`, los registros nuevos reciben premium hasta `TRIAL_ENDS_AT`. Después
de activarlo, concede la misma promoción a las cuentas existentes con `python manage.py
grant_trial_plan`; usa primero `python manage.py grant_trial_plan --dry-run` para revisar
cuántas cambiarían. Desactivar `TRIAL_MODE` restaura el registro gratuito sin migrar datos,
y las concesiones existentes caducan automáticamente en la fecha configurada.

**Advertencia:** premium significa **lecturas ilimitadas**. Con el saldo actual de la API
y un costo aproximado de medio centavo de dólar por lectura, unas decenas de personas
activas pueden agotar el saldo en pocas horas. Para el usuario, el síntoma será el 503
genérico «el servicio de interpretación no está disponible».

Antes de activar `TRIAL_MODE=True` en producción:

1. `MONTHLY_BUDGET` (B18) debe tener un valor real y su freno debe estar verificado con un test.
2. Revisa el throttle `reading_create`, actualmente en 10 por hora; con plan ilimitado es
   lo único que limita a un usuario individual y conviene considerar reducirlo.
3. Añade un tope diario global de lecturas, independiente del presupuesto en dólares, como
   segunda red. El presupuesto protege la billetera; el tope diario evita que un bucle la
   vacíe en minutos.


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

Los precios no están codificados en la aplicación. Antes de habilitar un modelo, crea en
el admin una fila `ModelPricing` con los precios vigentes por millón de tokens y su fecha
de inicio. Consulta siempre la [tabla oficial de precios de Claude](https://docs.claude.com/en/docs/about-claude/pricing).
Puedes registrar también los precios específicos de lectura y creación de caché; si se
omiten, el cálculo usa el precio normal de entrada. El costo queda materializado en cada
lectura, por lo que editar precios futuros no reescribe el histórico. `python manage.py
report_costs` muestra el total y promedio mensual, el desglose por modo y los diez usuarios
de mayor consumo.

El prompt de sistema se envía como bloque estable con caché efímera. Anthropic solo crea
una entrada cuando el prefijo alcanza el mínimo exigido por el modelo (y la reutilización
depende de que el prefijo sea idéntico y ocurra dentro del TTL); los contadores reales de
creación y lectura devueltos por la API son los que se guardan. Revisa los
[requisitos oficiales de prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
al cambiar de modelo.

## Despliegue en PythonAnywhere con frontend en Netlify

Sigue este orden; no hace falta que Django sirva archivos estáticos o medios en producción:

1. Crea el virtualenv, instala `requirements.txt` y configura en PythonAnywhere estas
   variables: `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`,
   `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `MONTHLY_BUDGET`,
   `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS`. Genera `SECRET_KEY` con:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Debe ser secreta y tener al menos 50 caracteres. Para un sitio Netlify en
   `https://astral999.netlify.app`, usa exactamente:

   ```dotenv
   CORS_ALLOWED_ORIGINS=https://astral999.netlify.app
   CSRF_TRUSTED_ORIGINS=https://astral999.netlify.app
   ```

   Sustituye ese host si Netlify asignó otro dominio; no añadas una barra final.
   En cuentas gratuitas añade `ANTHROPIC_PROXY=http://proxy.server:3128`: el cliente
   `httpx` enviará por él las solicitudes HTTPS a `api.anthropic.com`, incluido en la
   lista permitida de PythonAnywhere.

2. Aplica el esquema y recoge los estáticos:

   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

   `collectstatic` genera el directorio `staticfiles/`, incluidos los estilos del admin.

3. Carga **solo los 22 arcanos mayores** mientras B1b esté pendiente:

   ```bash
   python manage.py seed_cards --only=major
   ```

   No cargues aún el mazo completo: 56 cartas menores tienen el significado vacío y
   degradarían las lecturas.

4. En la pestaña **Web > Static files** de PythonAnywhere crea ambos mapeos (las rutas
   de disco son absolutas dentro de tu cuenta):

   | URL | Directorio |
   | --- | --- |
   | `/static/` | `<ruta-del-repo>/staticfiles` (`STATIC_ROOT`) |
   | `/media/` | `<ruta-del-repo>/media` (`MEDIA_ROOT`) |

   El segundo sirve tanto `share-images/` como imágenes de cartas. Es intencional que
   `config/urls.py` solo monte medios con `DEBUG=True`; en producción los entrega el
   servidor estático de PythonAnywhere.

5. Configura el archivo WSGI para importar `config.wsgi.application`, recarga la app y
   verifica antes de abrir tráfico:

   ```bash
   DEBUG=False SECRET_KEY='<clave-de-50+-caracteres>' \
     ALLOWED_HOSTS='<usuario>.pythonanywhere.com' python manage.py check --deploy
   ```

## Historial de lecturas fallidas

`GET /api/readings/` oculta por defecto las lecturas cuya generación falló. Para incluirlas
en el historial administrativo o durante un diagnóstico, usa
`GET /api/readings/?include_failed=true`. El detalle autenticado por id continúa disponible.

## Mazo provisional de desarrollo

Para probar el barajado, los patrones y las lecturas completas antes de disponer de los
significados definitivos en español, se conserva una copia del dataset
[`lsind18/tarot-json` de Kaggle](https://www.kaggle.com/datasets/lsind18/tarot-json) en
`apps/cards/fixtures/dev/`. Después de cargar el catálogo oficial, puede aplicarse así:

```bash
python manage.py seed_cards
python manage.py seed_dev_deck
# Opcional: copia también los JPG a MEDIA_ROOT/cards/
python manage.py seed_dev_deck --with-images
```

Este comando **solo es una semilla para desarrollo y pruebas**: reemplaza temporalmente
los significados con texto provisional en inglés, no crea cartas y se niega a ejecutarse
con `DEBUG=False` (salvo el escape explícito `--force`). No debe ejecutarse ni incluirse
como parte de una carga de datos en producción.

El origen de los significados es una guía publicada sin atribución dentro del dataset y
su autorización para uso comercial no está resuelta. Las ilustraciones Rider-Waite-Smith
de 1909 sí son de dominio público. Para mantener el repositorio compatible con revisiones
de texto, los JPG se guardan como archivos `*.jpg.base64`; `--with-images` los decodifica
al copiarlos a `MEDIA_ROOT`. En particular, las listas `light` y
`shadow` describen facetas que pueden aparecer en cualquier orientación: la semilla las
une en `meaning_up` y deja un marcador genérico inequívoco en `meaning_rev`; no interpreta
«sombra» como «invertida».

# Feedback de lecturas

Un usuario autenticado crea o reemplaza su voto con `POST` o `PUT` a
`/api/readings/<id>/feedback/` enviando `{"value": 1, "comment": "..."}` (o `-1`).
El resumen está disponible en `GET /api/readings/<id>/feedback/summary/`.

Las generaciones incluyen hasta tres lecturas positivas del mismo tipo como referencias de
estilo. Se puede ajustar con `FEEDBACK_FEW_SHOT_EXAMPLES` (entre 0 y 3; `0` desactiva la
inyección). Las respuestas negativas no se copian al prompt para no reforzar esos patrones.

Para exportar ejemplos revisables en JSONL:

```bash
python manage.py export_feedback_dataset --min-score 1 --limit 100 --output feedback.jsonl
```

El archivo es una base para few-shot. Antes de un eventual fine-tuning con otro proveedor debe
anonimizarse, revisarse y versionarse; no debe enviarse automáticamente a un modelo.
