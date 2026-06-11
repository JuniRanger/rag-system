# app/tools/schemas/supabase.py

SCHEMA_BUSCAR_VEHICULO = {
    "type": "function",
    "function": {
        "name": "buscar_por_vehiculo",
        "description": "Consulta el historial de reportes técnicos usando la marca y el modelo del auto.",
        "parameters": {
            "type": "object",
            "properties": {
                "marca": {"type": "string", "description": "Marca (ej. Hyundai)"},
                "modelo": {"type": "string", "description": "Modelo y año (ej. Santa Fe 2016)"}
            },
            "required": ["marca", "modelo"]
        }
    }
}

SCHEMA_BUSCAR_CATEGORIA = {
    "type": "function",
    "function": {
        "name": "buscar_por_categoria",
        "description": "Filtra reportes técnicos basados en la categoría del problema (ej. 'Battery', 'Transmission', 'Brakes').",
        "parameters": {
            "type": "object",
            "properties": {
                "categoria": {"type": "string", "description": "Nombre de la categoría técnica."}
            },
            "required": ["categoria"]
        }
    }
}

SCHEMA_BUSCAR_SEVERIDAD = {
    "type": "function",
    "function": {
        "name": "buscar_por_severidad",
        "description": "Recupera los casos registrados que coincidan con un nivel de severidad (ej. 'Alta', 'Baja', 'Crítica').",
        "parameters": {
            "type": "object",
            "properties": {
                "severidad": {"type": "string", "description": "Nivel de severidad asignado."}
            },
            "required": ["severidad"]
        }
    }
}

SCHEMA_BUSCAR_ESTATUS_TALLER = {
    "type": "function",
    "function": {
        "name": "buscar_por_estatus_taller",
        "description": "Lista los vehículos que se encuentran en un estado de reparación específico (ej. 'En progreso', 'Terminado').",
        "parameters": {
            "type": "object",
            "properties": {
                "estatus": {"type": "string", "description": "Estatus del flujo de taller."}
            },
            "required": ["estatus"]
        }
    }
}

SCHEMA_OBTENER_ECU = {
    "type": "function",
    "function": {
        "name": "obtener_datos_ecu",
        "description": "Extrae los datos crudos de la ECU y códigos de error almacenados de un vehículo usando su UUID.",
        "parameters": {
            "type": "object",
            "properties": {
                "record_id": {"type": "string", "description": "El UUID del registro en Supabase."}
            },
            "required": ["record_id"]
        }
    }
}

SCHEMA_BUSCAR_CODIGO_ECU = {
    "type": "function",
    "function": {
        "name": "buscar_por_codigo_error_ecu",
        "description": "Busca qué registros contienen un código de error específico dentro de sus datos de ECU.",
        "parameters": {
            "type": "object",
            "properties": {
                "codigo_error": {"type": "string", "description": "El código técnico a buscar (ej. '404_RIZZ', 'P0300')."}
            },
            "required": ["codigo_error"]
        }
    }
}

SCHEMA_SOLUCION_RAPIDA = {
    "type": "function",
    "function": {
        "name": "obtener_solucion_rapida",
        "description": "Recupera de forma directa únicamente el diagnóstico y la solución de un caso usando su UUID.",
        "parameters": {
            "type": "object",
            "properties": {
                "record_id": {"type": "string", "description": "El UUID del registro."}
            },
            "required": ["record_id"]
        }
    }
}

SCHEMA_CONTAR_MARCA = {
    "type": "function",
    "function": {
        "name": "contar_casos_por_marca",
        "description": "Devuelve la cantidad total de reportes e incidencias registradas en el sistema para una marca específica.",
        "parameters": {
            "type": "object",
            "properties": {
                "marca": {"type": "string", "description": "Marca a contabilizar (ej. Tesla, Toyota)."}
            },
            "required": ["marca"]
        }
    }
}

SCHEMA_LISTAR_ULTIMOS = {
    "type": "function",
    "function": {
        "name": "listar_ultimos_reportes",
        "description": "Obtiene una lista de los registros más recientes que han ingresado al taller.",
        "parameters": {
            "type": "object",
            "properties": {
                "limite": {"type": "integer", "description": "Cantidad de registros a traer. Por defecto 5."}
            }
        }
    }
}

SCHEMA_VERIFICAR_EXISTENCIA = {
    "type": "function",
    "function": {
        "name": "verificar_existencia_vehiculo",
        "description": "Verifica si un vehículo específico (marca y modelo) ya tiene antecedentes o registros previos en el sistema.",
        "parameters": {
            "type": "object",
            "properties": {
                "marca": {"type": "string"},
                "modelo": {"type": "string"}
            },
            "required": ["marca", "modelo"]
        }
    }
}