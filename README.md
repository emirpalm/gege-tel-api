# Gege Tel API — caso práctico

API mínima con **Python 3.12 + FastAPI + SQLite (SQLAlchemy 2)** para alta de líneas por empresa, webhook de red, beneficios con canje y un agente que no inventa beneficios.

## Correrlo (solo necesitas Docker)

```bash
docker compose run --rm tests        # 30 pruebas automáticas
docker compose up --build api        # API en http://localhost:8000  (docs: /docs)
```

Con la API levantada, `./demo.sh` hace el recorrido completo con `curl`.

> El agente usa por defecto un selector determinista (`AGENT_MODE=mock`). Para usar Claude:
> `AGENT_MODE=llm ANTHROPIC_API_KEY=sk-... docker compose up --build api`

## Identidad simulada

No hay inicio de sesión; la identidad se simula con encabezados:

| Encabezado      | Quién                  | Valores                                     |
|-----------------|------------------------|---------------------------------------------|
| `X-Company-Id`  | administradora / colaborador | `acme`, `globex`                      |
| `X-Line-Id`     | colaborador            | ID de la línea (`L-100` Acme básico, `L-200` Globex premium vienen sembradas) |

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/admin/lines` | Alta de colaborador `{employee_name, phone_number, plan: basic\|premium}`. Queda `pending` hasta que la red la active. |
| GET | `/admin/lines`, `/admin/lines/{id}` | Solo líneas de la empresa del encabezado. Otra empresa recibe **404**. |
| PATCH | `/admin/lines/{id}` | Cambio de plan (misma regla de aislamiento). |
| POST | `/webhooks/network` | Evento `{event_id, line_id, type, timestamp}`. Responde `applied`, `duplicate` o `ignored_stale`. |
| GET | `/me/benefits` | Beneficios vigentes del plan de la línea (sin códigos). |
| POST | `/me/benefits/{id}/redeem` | Canje: entrega el código. 409 si ya se canjeó este mes o la línea no está activa; 404 si no aplica. |
| POST | `/me/agent` | `{question}` → beneficios reales del plan o mensaje fijo. |

## Estructura

```
app/
  main.py            rutas HTTP (delgadas)
  deps.py            identidad por encabezados, reloj y selector inyectables
  models.py          tablas; reglas críticas como constraints (PK de event_id, UNIQUE de canje)
  clock.py           UTC para guardar, hora de CDMX para reglas de negocio
  services/
    network.py       webhook idempotente y tolerante a desorden
    benefits.py      elegibilidad (fuente única) y canje
    agent.py         selector (palabras clave o Claude) + guardrail
tests/               aislamiento, webhook, beneficios/canje, agente
```

Las decisiones, alternativas y uso de IA están en [DECISIONES.md](DECISIONES.md).
