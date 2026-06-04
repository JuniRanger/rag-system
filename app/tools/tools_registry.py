from app.tools.vehicle_tools import (
    diagnose_vehicle_problem,
    get_component_cost,
    get_vehicle_service_history,
    recommend_maintenance,
    check_vehicle_health,
    get_service_recommendation,
    estimate_repair_severity,
    get_vehicle_cost_estimate,
    detect_engine_issue,
    recommend_oil_change,
    predict_component_failure,
    get_repair_status,
    get_vehicle_region,
    recommend_brake_service,
    estimate_maintenance_priority
)


TOOLS = {

    "diagnose_vehicle_problem":
        diagnose_vehicle_problem,

    "get_component_cost":
        get_component_cost,

    "get_vehicle_service_history":
        get_vehicle_service_history,

    "recommend_maintenance":
        recommend_maintenance,

    "check_vehicle_health":
        check_vehicle_health,

    "get_service_recommendation":
        get_service_recommendation,

    "estimate_repair_severity":
        estimate_repair_severity,

    "get_vehicle_cost_estimate":
        get_vehicle_cost_estimate,

    "detect_engine_issue":
        detect_engine_issue,

    "recommend_oil_change":
        recommend_oil_change,

    "predict_component_failure":
        predict_component_failure,

    "get_repair_status":
        get_repair_status,

    "get_vehicle_region":
        get_vehicle_region,

    "recommend_brake_service":
        recommend_brake_service,

    "estimate_maintenance_priority":
        estimate_maintenance_priority,
}


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "diagnose_vehicle_problem",
            "description": "Diagnostica problemas vehiculares",
            "parameters": {
                "type": "object",
                "properties": {
                    "car_name": {"type": "string"},
                    "problem": {"type": "string"},
                },
                "required": ["car_name", "problem"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_cost_estimate",
            "description": "Estima costos de mantenimiento por marca",
            "parameters": {
                "type": "object",
                "properties": {
                    "brand": {
                        "type": "string"
                    }
                },
                "required": ["brand"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "detect_engine_issue",
            "description": "Detecta problemas de motor",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string"
                    }
                },
                "required": ["issue"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "recommend_oil_change",
            "description": "Recomienda cambio de aceite",
            "parameters": {
                "type": "object",
                "properties": {
                    "mileage": {
                        "type": "integer"
                    }
                },
                "required": ["mileage"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "predict_component_failure",
            "description": "Predice fallas de componentes",
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string"
                    }
                },
                "required": ["component"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_repair_status",
            "description": "Consulta estado de reparación",
            "parameters": {
                "type": "object",
                "properties": {
                    "car_name": {
                        "type": "string"
                    }
                },
                "required": ["car_name"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_vehicle_region",
            "description": "Obtiene región del vehículo",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string"
                    }
                },
                "required": ["model"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "recommend_brake_service",
            "description": "Recomienda servicio de frenos",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {
                        "type": "string"
                    }
                },
                "required": ["problem"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "estimate_maintenance_priority",
            "description": "Estima prioridad de mantenimiento",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string"
                    }
                },
                "required": ["issue"]
            }
        }
    },
    
    {
        "type": "function",
        "function": {
            "name": "get_component_cost",
            "description": "Consulta costo de componentes vehiculares",
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {"type": "string"},
                },
                "required": ["component"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_service_history",
            "description": "Consulta historial de servicios",
            "parameters": {
                "type": "object",
                "properties": {
                    "car_model": {"type": "string"},
                },
                "required": ["car_model"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_maintenance",
            "description": "Recomienda mantenimiento vehicular",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_issue": {"type": "string"},
                },
                "required": ["vehicle_issue"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_vehicle_health",
            "description": "Evalua el estado general del vehiculo",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_status": {"type": "string"},
                },
                "required": ["vehicle_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_recommendation",
            "description": "Recomienda servicio por kilometraje",
            "parameters": {
                "type": "object",
                "properties": {
                    "mileage": {"type": "integer"},
                },
                "required": ["mileage"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_repair_severity",
            "description": "Estima severidad de reparacion",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {"type": "string"},
                },
                "required": ["problem"],
            },
        },
    },
]
