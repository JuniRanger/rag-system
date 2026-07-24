# Herramientas (Function Calling)

No hay MCP en este repositorio. Las tools son **function calling nativo de Ollama**.

Registro: `register_all_tools()` en lifespan (`app/tools/__init__.py`).

## Condiciones de registro

1. Si `ENABLE_RAG_TOOLS=false` → **no se registra ninguna tool**.
2. Si Supabase configurado (`URL` + `SERVICE_ROLE_KEY` + `TABLE`) → registra **10 tools de lectura**.
3. Siempre (si tools enabled) → registra **`crearCitaAPI`**.

Componentes:

| Módulo | Rol |
| ------ | --- |
| `app/tools/registry.py` | Catálogo singleton |
| `app/tools/executor.py` | Ejecuta `tool.run(**arguments)` con manejo de errores |
| `app/tools/schemas/` | Schemas JSON estilo Ollama (descripciones para el modelo) |
| `app/tools/implementations/` | Lógica de negocio |
| `app/rag/tool_loop.py` | Rondas de tool calling, filtros por rol/modo |

## Disponibilidad por modo y rol

Definido en `tool_loop.py`:

| Condición | Tools expuestas al modelo |
| --------- | ------------------------- |
| `tool_mode=scheduling` | Solo `crearCitaAPI` |
| `tool_mode=all` | Todas las registradas |
| `tool_mode=none` | Ninguna |
| `user_role=admin` | Se excluye `crearCitaAPI` del schema y se bloquea en ejecución |
| Admin + scheduling | Respuesta fija `ADMIN_SCHEDULING_DENIED` (sin tools) |

Máximo de rondas: **4** (`MAX_TOOL_ROUNDS`).

## Tools Supabase (solo lectura)

Implementación: `app/tools/implementations/supabase/read_tools.py`.  
Tabla: `settings.SUPABASE_TABLE`. Límite default de filas: 20.

| Nombre | Descripción breve | Parámetros |
| ------ | ----------------- | ---------- |
| `buscar_por_vehiculo` | Reportes por marca/modelo | `marca`, `modelo` |
| `buscar_por_categoria` | Por categoría de problema | `categoria` |
| `buscar_por_severidad` | Por severidad | `severidad` |
| `buscar_por_estatus_taller` | Por `repair_status` | `estatus` |
| `obtener_datos_ecu` | ECU por UUID | `record_id` |
| `buscar_por_codigo_error_ecu` | Busca código en `ecu_data` | `codigo_error` |
| `obtener_solucion_rapida` | Diagnóstico/solución por id | `record_id` |
| `contar_casos_por_marca` | Conteo por marca | `marca` |
| `listar_ultimos_reportes` | Últimos N por `created_at` | `limite` (opcional) |
| `verificar_existencia_vehiculo` | Existe historial marca/modelo | `marca`, `modelo` |

**Nota:** `admin_tools.py` y `write_tools.py` existen pero están **vacíos** (sin tools de escritura registradas). Coherente con las reglas de prompts que prohíben modificar la BD.

## Tool de citas

| Nombre | Endpoint | Args LLM | Args inyectados servidor |
| ------ | -------- | -------- | ------------------------ |
| `crearCitaAPI` | `POST {CITAS_API_BASE_URL}/citas/agendar` | `fecha`, `vehiculo`, `producto` | `usuario: {id, nombre, correo}` desde `RAGRequest.user` |

Schema: `app/tools/schemas/citas.py`.  
Implementación: `app/tools/implementations/citas.py`.

El LLM **no** debe enviar `usuario`; `_inject_cita_usuario` lo adjunta en el tool loop. Si faltan id/nombre/correo en el request, la tool devuelve error.

## Relación con prompts

- Prompt principal del agente: [prompts/agent.md](./prompts/agent.md)
- Descripciones de schemas actúan como micro-instrucciones al modelo en la misma llamada `chat_with_tools`.
- Tras tools sin content final se usa `TOOL_FINAL_USER_NUDGE`.
- `_strip_tool_json_leak` evita filtrar JSON/tool syntax al usuario.

## Ver también

- [flows.md](./flows.md) — diagrama del tool loop
- [intents.md](./intents.md) — cuándo se activa cada `tool_mode`
- [environment.md](./environment.md) — `ENABLE_RAG_TOOLS`, `CITAS_API_BASE_URL`
