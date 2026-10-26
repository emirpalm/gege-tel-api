# Gege Tel API — Decisiones técnicas

**Autor:** Emir · **Repositorio:** https://github.com/emirpalm/gege-tel-api · **Tiempo real:** ≈2 h 30 min

## 1. Las tres decisiones más importantes

### 1.1 Las reglas críticas viven en la base de datos, no solo en el código

- **Webhook duplicado:** `network_events.event_id` es **PRIMARY KEY**. Un reenvío choca con la PK y se responde `200 duplicate` sin tocar la línea; responder 200 (no 409) evita que la red reintente para siempre.
- **Desorden:** la línea guarda `last_event_at`. El estado se cambia con un **UPDATE condicional atómico** (`... WHERE last_event_at IS NULL OR last_event_at < :ts`); si no afecta filas, el evento se guarda como `ignored_stale` para auditoría. La red es la fuente de verdad: gana el evento más reciente, sin máquina de estados estricta (si se pierde un evento, el siguiente igual deja la línea en el estado correcto).
- **Doble canje:** `UNIQUE(line_id, benefit_id, period)` donde `period` es el mes (`2026-10`). Dos peticiones simultáneas no pueden pasar ambas.
- **Descartado:** "SELECT y luego INSERT" o IDs procesados en memoria: funcionan en la demo pero tienen condición de carrera y se pierden al reiniciar.

### 1.2 Aislamiento multiempresa en una sola capa, con 404

- La empresa sale de `X-Company-Id` (dependencia de FastAPI). **Toda** búsqueda de línea pasa por `get_company_line()`, que filtra `company_id` *dentro* de la consulta.
- Otra empresa recibe **404, no 403**: no puede ni confirmar que la línea existe.
- El colaborador se identifica con empresa + línea, así que tampoco puede usar una línea ajena.
- **Descartado:** una BD por empresa (excesivo para 2 empresas) y Row-Level Security (SQLite no lo tiene; sería el siguiente paso con Postgres).

### 1.3 El agente no puede inventar *por construcción*

- El backend calcula la **lista cerrada** de beneficios elegibles (plan + vigencia) con la misma función que usan el listado y el canje.
- El "selector" (palabras clave por defecto, o Claude con `AGENT_MODE=llm`) **solo elige IDs** de esa lista; con Claude, el JSON schema limita los valores a un `enum` de los IDs elegibles.
- **Guardrail:** los IDs devueltos se intersectan con la lista elegible y la respuesta se arma con plantilla desde la BD. Una prueba usa un "LLM falso" que devuelve IDs inexistentes, vencidos y de otro plan: no sobreviven.
- **El agente no entrega códigos**: el código solo sale del canje, que es donde se aplica la regla de una vez al mes. Si el agente diera códigos, se podría saltar esa regla.
- **Descartado:** dejar que el LLM redacte libremente con el catálogo en el prompt y "pedirle que no invente". Eso reduce las alucinaciones, pero no las elimina, y no se puede probar de forma determinista.

### Otras decisiones menores

- **Tiempo:** se guarda en UTC; "vigente hoy" y "el mes" se evalúan en hora de **Ciudad de México** (un canje el 31/10 a las 21:00 CDMX cuenta para octubre). El webhook exige timestamps con zona horaria.
- **Reloj inyectable** (`get_now`): las pruebas mueven la fecha para vencimientos y cambio de mes.
- **Estado inicial `pending`:** una línea recién dada de alta no puede canjear hasta que la red la active.
- **Docker:** `docker compose run --rm tests` y `docker compose up api`, sin instalar Python localmente.

## 2. Uso de IA

- **Herramientas:** Claude Code (Claude Opus 5.5) para scaffold, pruebas y revisión; yo definí la arquitectura y revisé cada archivo.
- **Error de la IA y cómo lo detecté:** la primera versión del agente trataba como "pregunta general" cualquier pregunta que contuviera la palabra *beneficio*. Así, «¿tengo beneficios en Starbucks?» habría listado **todos** los beneficios del plan, es decir, una respuesta sobre algo que no existe. Lo detecté al escribir los casos negativos de la prueba "el agente no inventa". La corrección: la pregunta solo es general si **todas** sus palabras son de relleno ("qué", "tengo", "beneficios"…); cualquier palabra extra lleva al mensaje fijo.
- _<agregar aquí cualquier otro error que hayas visto tú>_
- **Riesgo anticipado:** comparar timestamps como texto ordena mal los eventos con offsets (`05:00-06:00` es *después* de `10:00Z`). Se normaliza a UTC y hay una prueba específica.

## 3. Qué dejaría para después

1. **Autenticación real** (JWT con `company_id` y rol en claims) en vez de encabezados.
2. **Firma HMAC del webhook** y lista de IPs de la red; hoy cualquiera podría enviar eventos.
3. **Postgres + Alembic**, con RLS por `company_id` como segunda barrera.
4. **Cola para el webhook** (responder 202 y procesar async) si el volumen crece; la idempotencia ya está lista para reintentos.
5. **Eventos para líneas aún no registradas:** hoy responden 404 y la red reintenta; con más tiempo los guardaría en un buzón y los aplicaría al darse de alta la línea.
6. **Agente:** evaluación con preguntas reales; Claude como selector con caché del system prompt; multi-turno.
7. **Catálogo administrable**, historial de canjes y observabilidad (logs estructurados, métricas por resultado del webhook).

## 4. Tiempo real

**≈2 h 30 min en total** (26/10/2026). Desglose estimado por fase:

| Fase | Tiempo estimado | Qué incluyó |
|---|---|---|
| Análisis | ~20 min | Lectura del enunciado, reglas ambiguas y supuestos: estado inicial `pending`, mes en hora de CDMX, empate de timestamps, línea desconocida en el webhook, el agente no entrega códigos. |
| Arquitectura y modelo de datos | ~25 min | Capas (rutas → dependencias → servicios → modelos), tablas y qué reglas van como constraints de BD; identidad por encabezados; diseño del agente con lista cerrada y guardrail. |
| Implementación | ~45 min | Modelos, seed, webhook, canje, agente (selector por palabras clave + Claude opcional) y rutas, con Claude Code. |
| Pruebas | ~30 min | 30 pruebas automáticas; casos negativos del agente (aquí se detectó el error de la IA) y corrección. |
| Docker y demo | ~10 min | `Dockerfile`, `docker-compose.yml` y `demo.sh` ejecutado contra el contenedor. |
| Revisión, repositorio y documento | ~20 min | Revisión del código, README, este documento y publicación en GitHub. |
| **Total** | **≈2 h 30 min** | |
