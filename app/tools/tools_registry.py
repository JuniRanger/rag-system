from app.tools.vehicle_tools import (
    diagnose_vehicle_problem,
    get_component_cost,
    get_vehicle_service_history,
    recommend_maintenance,
    check_vehicle_health,
    get_service_recommendation,
    estimate_repair_severity
)


TOOLS = {
    "diagnose_vehicle_problem": diagnose_vehicle_problem,
    "get_component_cost": get_component_cost,
    "get_vehicle_service_history": get_vehicle_service_history,
    "recommend_maintenance": recommend_maintenance,
    "check_vehicle_health": check_vehicle_health,
    "get_service_recommendation": get_service_recommendation,
    "estimate_repair_severity": estimate_repair_severity,
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
                    "car_name": {
                        "type": "string"
                    },
                    "problem": {
                        "type": "string"
                    }
                },
                "required": [
                    "car_name",
                    "problem"
                ]
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
                    "component": {
                        "type": "string"
                    }
                },
                "required": [
                    "component"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_service_history",
            "description": "Consulta historial de servicios",
            "parameters": {
                "type": "object",
                "properties": {
                    "car_model": {
                        "type": "string"
                    }
                },
                "required": [
                    "car_model"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_maintenance",
            "description": "Recomienda mantenimiento vehicular",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_issue": {
                        "type": "string"
                    }
                },
                "required": [
                    "vehicle_issue"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_vehicle_health",
            "description": "Evalúa estado del vehículo",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_status": {
                        "type": "string"
                    }
                },
                "required": [
                    "vehicle_status"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_service_recommendation",
            "description": "Recomienda servicio por kilometraje",
            "parameters": {
                "type": "object",
                "properties": {
                    "mileage": {
                        "type": "integer"
                    }
                },
                "required": [
                    "mileage"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_repair_severity",
            "description": "Estima severidad de reparación",
            "parameters": {
                "type": "object",
                "properties": {
                    "problem": {
                        "type": "string"
                    }
                },
                "required": [
                    "problem"
                ]
            }
        }
    }
]