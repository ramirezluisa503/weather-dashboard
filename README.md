# 🌡️ Weather Dashboard

Dashboard full stack que **compara el clima de dos ciudades en tiempo real**. Consulta [OpenWeather](https://openweathermap.org/), guarda el histórico en PostgreSQL, usa Redis como caché y notifica a todos los navegadores conectados por WebSocket cada vez que llega una medición nueva. Todo se levanta con un solo `docker compose up`.

![Captura del dashboard comparando Bogotá y Cartagena](docs/captura-dashboard.jpg)

> **Video de presentación:** [enlace pendiente]

**Stack:** Django 6 · Django REST Framework · Django Channels (Daphne) · PostgreSQL 17 · Redis 7 · React 19 · Vite · Ant Design · Recharts · Nginx · Docker Compose

---

## Funcionalidades

- **Comparación de dos ciudades** con tarjetas de temperatura, humedad y viento.
- **Diseño que cambia con el clima:** cada ciudad aporta su foto de fondo y su color según su temperatura (frío, templado, cálido, caluroso).
- **Gráfico de series de tiempo** comparando temperatura, humedad o viento de ambas ciudades.
- **Histórico** en tabla con **paginación del servidor** y **filtro por ciudad**.
- **Exportación a CSV** (exporta exactamente lo filtrado).
- **Tiempo real:** la UI se actualiza sola cuando se guarda una medición nueva, con **reconexión automática** del WebSocket y estado de la conexión visible.
- **Resiliencia:** si OpenWeather falla, responde con el último dato guardado e informa al usuario.
- **Responsive**, estados de carga y mensajes de error en español.
- **API documentada** con Swagger.

---

## Cómo levantar el proyecto

**Requisitos:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (con Docker Compose) y una API key gratuita de [OpenWeather](https://home.openweathermap.org/users/sign_up).

```bash
git clone https://github.com/ramirezluisa503/weather-dashboard.git
cd weather-dashboard
cp .env.example .env          # en Windows (CMD): copy .env.example .env
```

Abre `.env` y escribe tu API key en `OPENWEATHER_API_KEY`. El resto de valores de ejemplo funciona para un entorno local.

```bash
docker compose up --build
```

| Servicio | URL |
|---|---|
|  **Dashboard** | http://localhost:5173 |
|  Documentación de la API (Swagger) | http://localhost:8000/api/docs/ |
|  API REST | http://localhost:8000/api/ |

Las migraciones se aplican solas al arrancar. La base de datos empieza vacía y se llena a medida que se consultan ciudades.

> 💡 Una API key nueva de OpenWeather puede tardar hasta 2 horas en activarse. Mientras tanto, la API responde `401` y el dashboard lo informa.

<details>
<summary><b>Desarrollo local del frontend (con recarga en caliente)</b></summary>

```bash
docker compose stop frontend      # libera el puerto 5173
cd frontend
npm install
npm run dev                       # http://localhost:5173
```
</details>

---

## ⚙️ Variables de entorno

Definidas en `.env` (no se versiona) a partir de [`.env.example`](.env.example) (sin valores reales).

| Variable | Descripción | Valor de ejemplo |
|---|---|---|
| `OPENWEATHER_API_KEY` | API key de OpenWeather (**obligatoria**) | — |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Base de datos y credenciales. La imagen de PostgreSQL las crea en el primer arranque | `weather` / `weather_user` / `change_me` |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Host y puerto de PostgreSQL. `db` es el nombre del servicio en Docker | `db` / `5432` |
| `DJANGO_SECRET_KEY` | Clave secreta de Django | `change_me` |
| `DJANGO_DEBUG` | Modo depuración (`True`/`False`). Por defecto `False` si falta | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hosts aceptados por Django, separados por coma | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | Frontends autorizados a consumir la API desde el navegador | `http://localhost:5173` |
| `REDIS_URL` | Redis para la caché y el channel layer | `redis://redis:6379/0` |
| `WEATHER_CACHE_TTL_SECONDS` | **TTL de la caché** por ciudad, en segundos | `600` (10 min) |

El frontend usa además `VITE_API_URL` (argumento de build, por defecto `http://localhost:8000`): es la URL del backend **tal como la ve el navegador**, no el contenedor.

---

## Arquitectura

![Diagrama de arquitectura de Weather Dashboard](docs/arquitectura.svg)

El navegador descarga la SPA de React desde Nginx y luego habla directamente con el backend Django: peticiones REST para consultar, paginar y exportar datos, y un WebSocket permanente para recibir actualizaciones. Ante cada consulta, la capa de servicio busca primero en Redis (caché de 10 min); solo si no hay dato llama a OpenWeather, guarda la medición en PostgreSQL y, si la API falla, responde con el último dato guardado. Cada medición nueva se publica en el channel layer de Redis y Django Channels la reenvía por WebSocket, así todos los navegadores conectados se actualizan sin recargar. PostgreSQL y Redis solo son accesibles desde la red interna de Docker.

### Backend en capas

Cada capa solo llama a la de abajo: las views nunca hablan directamente con la base de datos ni con OpenWeather.

| Capa | Archivo | Responsabilidad |
|---|---|---|
| Controlador | `views.py` + `serializers.py` | HTTP: valida la entrada y traduce errores a códigos (400 / 404 / 503) |
| Servicio | `services.py` | Lógica: caché → OpenWeather → fallback a la BD → evento WebSocket |
| Cliente externo | `openweather_client.py` | Único módulo que llama a OpenWeather (timeout, errores propios) |
| Repositorio | `repositories.py` | Consultas al ORM reutilizables (deduplicación, último dato, histórico) |
| Modelo | `models.py` | `WeatherData` con índice `(city, -timestamp)` y restricción única `(city, timestamp)` |
| Tiempo real | `consumers.py` + `routing.py` | Consumer WebSocket y rutas de Channels |

###  Estructura del proyecto

```
weather-dashboard/
├── docker-compose.yml             # 4 servicios: db, redis, backend, frontend
├── .env.example                   # variables de entorno (sin valores reales)
├── README.md
│
├── docs/
│   ├── arquitectura.svg           # diagrama de arquitectura
│   └── captura-dashboard.jpg      # captura para el README
│
├── backend/                       # Django + DRF + Channels
│   ├── Dockerfile                 # Python 3.13-slim
│   ├── .dockerignore
│   ├── requirements.txt           # dependencias con versión fija
│   ├── manage.py
│   │
│   ├── config/                    # configuración del proyecto
│   │   ├── settings.py            # lee todo de variables de entorno
│   │   ├── urls.py                # /api/, /api/docs/, /admin/
│   │   ├── asgi.py                # HTTP → Django · WebSocket → Channels
│   │   └── wsgi.py
│   │
│   └── weather/                   # app del dominio del clima
│       ├── models.py              # modelo WeatherData
│       ├── migrations/            # historial de la base de datos
│       ├── openweather_client.py  # cliente de la API externa
│       ├── repositories.py        # consultas al ORM
│       ├── services.py            # lógica: caché → API → fallback
│       ├── serializers.py         # validación de entrada y JSON
│       ├── views.py               # controladores (endpoints REST)
│       ├── pagination.py          # paginación del histórico
│       ├── urls.py                # rutas de la API
│       ├── consumers.py           # consumer WebSocket
│       ├── routing.py             # rutas WebSocket (/ws/weather/)
│       ├── tests.py               # 12 tests del backend
│       ├── admin.py
│       └── apps.py
│
└── frontend/                      # React + Vite + Ant Design
    ├── Dockerfile                 # multi-stage: Node construye, Nginx sirve
    ├── nginx.conf                 # servidor de los archivos estáticos
    ├── .dockerignore
    ├── package.json               # dependencias y scripts
    ├── package-lock.json
    ├── vite.config.js
    ├── eslint.config.js
    ├── index.html
    │
    ├── public/                    # se sirve tal cual
    │   ├── icons/termometro.svg   # ícono de la pestaña
    │   └── images/                # fondos por temperatura
    │       ├── cold.webp          # frío (< 12 °C)
    │       ├── mild.webp          # templado (12–20 °C)
    │       ├── warm.webp          # cálido (20–28 °C)
    │       └── hot.webp           # caluroso (≥ 28 °C)
    │
    └── src/
        ├── main.jsx               # punto de entrada + tema de Ant Design
        ├── App.jsx                # vistas, estado y tiempo real
        ├── index.css              # estilos globales (vidrio, responsive)
        │
        ├── api/
        │   └── weatherApi.js      # único módulo que habla con el backend
        │
        ├── hooks/
        │   ├── useDashboard.js        # datos de las dos ciudades
        │   ├── useWeatherHistory.js   # histórico paginado
        │   └── useWeatherSocket.js    # WebSocket con reconexión
        │
        ├── components/
        │   ├── Navbar.jsx             # navegación y estado en vivo
        │   ├── CitySelector.jsx       # selección de ciudades
        │   ├── WeatherCard.jsx        # tarjeta del clima actual
        │   ├── ComparisonChart.jsx    # gráfico de comparación
        │   ├── HistoryTable.jsx       # tabla, filtro y exportar CSV
        │   └── Background.jsx         # fondo dividido por ciudad
        │
        └── utils/
            └── weatherTheme.js    # temas visuales por temperatura
```

---

##  API

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/api/dashboard-data/?city1=&city2=` | Endpoint optimizado del dashboard: clima actual de las dos ciudades + últimos 24 registros de cada una, en **una sola petición** |
| `GET` | `/api/weather/?city=&page=&page_size=` | Histórico **paginado** (10 por defecto, máximo 100) con filtro opcional por ciudad |
| `GET` | `/api/weather/export/?city=` | Exportación del histórico a **CSV** (streaming) |
| `WS` | `/ws/weather/` | Eventos `weather_created` cada vez que se guarda una medición nueva |

La ruta de la prueba `GET /weather/` se expone como `/api/weather/` (prefijo `/api/` para separar la API de otras rutas). Documentación interactiva en **`/api/docs/`**.

Cada respuesta del clima actual incluye `"source": "cache" | "api" | "database"`, para indicar de dónde salió el dato.

---

##  Decisiones técnicas y trade-offs

| Decisión | Por qué | Alternativa descartada |
|---|---|---|
| **Arquitectura en capas** (controlador → servicio → repositorio → modelo) | La lógica de caché, API externa y fallback vive en un solo lugar y es fácil de probar; cambiar de proveedor del clima solo toca el cliente | MVT "puro" con lógica en las views; Clean/Hexagonal (excesiva para el alcance) |
| **Caché Redis por ciudad con TTL de 600 s** | El clima no cambia en segundos y OpenWeather actualiza cada ~10 min: se responde en milisegundos y se protege la cuota del plan gratuito. Redis es una copia temporal; **PostgreSQL es la fuente de verdad** | Sin caché (lento y gasta la cuota); TTL largo (datos desactualizados) |
| **Fallback a la BD** si OpenWeather falla | El usuario recibe el último dato guardado, marcado como `source: "database"` y avisado en la UI. Si no hay datos, `503` claro en vez de inventar | Responder error siempre |
| **Deduplicación en dos capas** | `get_or_create` evita duplicados en el código y la restricción única de la BD los impide incluso con peticiones simultáneas | Solo validar en el código |
| **Paginación en el servidor** + QuerySets perezosos | PostgreSQL devuelve solo las filas de la página (`LIMIT/OFFSET`): el tiempo no depende del tamaño del histórico. `max_page_size=100` protege la BD | Paginar en el frontend (descargaría todo) |
| **`/dashboard-data/` optimizado** | Una petición en vez de cuatro, clima actual desde caché, histórico limitado y con `.values()` | Varias peticiones desde el frontend |
| **Consultas a OpenWeather en paralelo** (`ThreadPoolExecutor`) | Es espera de red (I/O): el tiempo sin caché bajó de ~0,8 s a ~0,36 s (−55 %). Se cierra la conexión a la BD de cada hilo | Consultas secuenciales |
| **CSV en streaming** (`StreamingHttpResponse` + generadores) | La memoria no crece con el tamaño del histórico. Incluye BOM para que Excel muestre bien las tildes | Generar el archivo completo en memoria |
| **WebSocket con Django Channels**, Redis como channel layer | El servidor avisa cuando hay datos nuevos, sin polling. Redis ya estaba en el stack | Polling desde el frontend |
| **El evento solo se emite si el registro es nuevo** y su fallo no rompe la petición | Respeta "emitir eventos al insertar datos"; el tiempo real es un complemento, el dato ya quedó guardado | Emitir en cada consulta |
| **Reconexión con backoff exponencial** (1 s → 30 s) | Se recupera sola tras caídas sin saturar al servidor | Reintentos constantes |
| **Frontend con Nginx (Dockerfile multi-stage)** | La imagen final solo tiene Nginx y los estáticos: más liviana y segura | Servidor de desarrollo de Vite dentro del contenedor |
| **Fondo dividido por ciudad** | Con el promedio de temperaturas, París (2 °C) + Cartagena (30 °C) daba "templado", que no representaba a ninguna | Un solo fondo por temperatura promedio |
| **Navbar con dos vistas** (Comparación / Histórico) | Reduce el scroll; las vistas se ocultan sin desmontarse para conservar el filtro y la página de la tabla | Una sola página larga |

---

## Resiliencia y seguridad

- **OpenWeather:** timeout de 5 s y excepciones propias (`CityNotFoundError` → 404, `OpenWeatherError` → fallback a la BD → 503 si no hay datos).
- **Logs claros** con fecha, nivel y módulo (`Cache HIT/MISS`, `Fallback a la BD`, `Nuevo registro`…). Los errores de conexión no imprimen la URL para **no filtrar la API key**.
- **Validación de entrada** con serializers: lista blanca de caracteres para la ciudad (letras con tildes, espacios, `-`, `.`, `'`) y longitud máxima → `400` con mensaje en español.
- **SQL injection:** el ORM de Django usa consultas parametrizadas. **XSS:** la API responde JSON, la validación rechaza `<` y `>`, y React escapa el contenido.
- **CORS** con lista blanca de orígenes (no se permite cualquier origen). **WebSockets** protegidos con `AllowedHostsOriginValidator`, ya que no tienen protección CSRF. La API solo expone métodos `GET`.
- **Secretos** solo en `.env` (ignorado por Git); `.env.example` sin valores reales. PostgreSQL y Redis no publican puertos fuera de Docker.

---

##  Tests

El backend tiene **12 tests** de los puntos críticos. Con los contenedores encendidos:

```bash
docker compose exec backend python manage.py test weather -v 2
```

| Qué se prueba | Tests |
|---|---|
| Caché: la segunda consulta no llama a OpenWeather | `test_segunda_consulta_sale_de_la_cache` |
| Fallback a la BD si OpenWeather falla · error si no hay datos | `test_fallback_a_la_bd_si_openweather_falla`, `test_sin_datos_y_api_caida_lanza_error` |
| Deduplicación de mediciones | `test_misma_medicion_no_se_duplica` |
| `/dashboard-data/`: orden, 404, 503 y 400 | `test_devuelve_las_dos_ciudades_en_orden`, `test_ciudad_inexistente_responde_404`, `test_api_caida_sin_datos_responde_503`, `test_misma_ciudad_responde_400` |
| `/weather/`: paginación, filtro y validación | `test_paginacion_del_backend`, `test_filtro_por_ciudad_normalizada`, `test_ciudad_con_caracteres_invalidos_responde_400` |
| Exportación CSV filtrada | `test_exporta_csv_filtrado` |

- OpenWeather se **simula** con `unittest.mock`: los tests no dependen de internet ni de la cuota de la API.
- Caché y channel layer **en memoria** durante los tests; Django usa una base de datos de prueba que crea y borra sola.
- El dashboard se prueba con `TransactionTestCase`, porque consulta las ciudades en hilos con su propia conexión a la BD.

---

##  Limitaciones y mejoras futuras

- **Sin refresco periódico (Celery):** las mediciones nuevas llegan cuando alguien consulta una ciudad con la caché vencida. La UI se actualiza **por eventos, no por tiempo**, y el histórico puede tener huecos (por ejemplo, de noche). Mejora: tarea programada con Celery cada 10 minutos, que se complementa con el WebSocket.
- **Sin tests del frontend:** se verificó manualmente y con capturas en distintos tamaños de pantalla.
- **El bundle de JavaScript supera los 500 KB** (Ant Design + Recharts). Mejora: división de código con `import()` dinámico.
- **Los temas visuales dependen solo de la temperatura** (no del estado del cielo), porque el modelo no guarda esa información.
- **El backend usa el servidor de desarrollo ASGI** (`runserver` con Daphne) con `DEBUG=True`, pensado para la ejecución local de la prueba. En producción: Daphne/Uvicorn directo, `DEBUG=False` y archivos estáticos servidos aparte.
- Frontend en **JavaScript** por tiempo; con más tiempo usaría TypeScript.
- Mejoras posibles: integración continua (GitHub Actions) para correr los tests en cada push.

---

##  Parte B (agente con tools)

No implementada: siguiendo el criterio de la prueba de priorizar *"un alcance mínimo completo sobre un alcance amplio a medias"*, me enfoqué en entregar la Parte A completa, probada y documentada.

---

##  Tiempo invertido

| Día | Horas | Trabajo |
|---|---|---|
| Martes 24 nov | ~2 h | Preparación: entorno, API key, configuración, decisión de arquitectura |
| Miércoles 25 nov | ~2 h | Proyecto Django, modelo, configuración por variables de entorno |
| Jueves 26 nov | ~10 h | Docker, backend completo (caché, servicio, endpoints, CSV, Swagger, WebSockets) y frontend |
| Viernes 27 nov | [pendiente] | Frontend en Docker, rendimiento, tests, diagrama, README |
| Sábado 28 / Domingo 29 nov | [pendiente] | [pendiente] |
| **Total** | **[pendiente]** | |

---

##  Uso de IA

Desarrollé el proyecto con apoyo de **Claude Code** (modelo Claude Opus 5.5, extensión de VS Code) y **Claude**, usándolos como **tutor y asistente paso a paso**: para explicar conceptos, proponer alternativas con sus trade-offs, revisar mi código, diagnosticar errores y verificar el resultado. Tomé las decisiones técnicas y de diseño, escribí gran parte del código y validé cada paso en mi máquina antes de avanzar.

---

## Créditos

- **Imágenes de fondo:** fotografías de [Pexels](https://www.pexels.com), usadas bajo la [Licencia de Pexels](https://www.pexels.com/es-es/licencia/) (uso gratuito, atribución no obligatoria). Optimizadas a WebP (~300 KB cada una).
- **Ícono:** termómetro dibujado en SVG para este proyecto.
