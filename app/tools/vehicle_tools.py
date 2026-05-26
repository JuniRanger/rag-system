import pandas as pd
from pathlib import Path


BASE_DATASET_PATH = Path("datasets")


# =========================
# DATASETS
# =========================

diagnostic_df = pd.read_csv(
    BASE_DATASET_PATH / "ML Car Diagnostic Agent AI Assistant.csv"
)

components_df = pd.read_csv(
    BASE_DATASET_PATH / "Vehicle Maintenance- Standard Components Cost.csv"
)

service_df = pd.read_csv(
    BASE_DATASET_PATH / "Vehicle Maintenance- Service Records.csv"
)


# =========================
# TOOLS
# =========================

def diagnose_vehicle_problem(car_name: str, problem: str) -> str:
    """
    Diagnostica problemas vehiculares.

    Args:
        car_name: Nombre del vehículo
        problem: Problema reportado
    """

    matches = diagnostic_df[
        diagnostic_df["Problem"].str.contains(
            problem,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré diagnóstico para ese problema."

    row = matches.iloc[0]

    return (
        f"Vehículo: {car_name}\n"
        f"Problema: {problem}\n"
        f"Diagnóstico: {row['Diagnostic']}\n"
        f"Solución: {row['Solution']}\n"
        f"Severidad: {row['Severity']}"
    )


def get_component_cost(component: str) -> str:
    """
    Consulta costo de componentes vehiculares.

    Args:
        component: Nombre del componente
    """

    matches = components_df[
        components_df["Component"].str.contains(
            component,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré el componente solicitado."

    row = matches.iloc[0]

    return (
        f"Componente: {row['Component']}\n"
        f"Costo: {row['Price']}"
    )


def get_vehicle_service_history(car_model: str) -> str:
    """
    Consulta historial de servicios vehiculares.

    Args:
        car_model: Modelo del vehículo
    """

    matches = service_df[
        service_df["Car Model"].str.contains(
            car_model,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré historial de servicios."

    row = matches.iloc[0]

    return (
        f"Vehículo: {row['Car Model']}\n"
        f"Servicio: {row['Service Task']}\n"
        f"Kilometraje: {row['Mileage Interval']}"
    )


def recommend_maintenance(vehicle_issue: str) -> str:
    """
    Recomienda mantenimiento basado en síntomas.

    Args:
        vehicle_issue: Problema o síntoma detectado
    """

    if "brake" in vehicle_issue.lower():
        return "Se recomienda revisión completa del sistema de frenos."

    if "battery" in vehicle_issue.lower():
        return "Se recomienda revisar batería y sistema eléctrico."

    if "engine" in vehicle_issue.lower():
        return "Se recomienda diagnóstico completo del motor."

    return "Se recomienda inspección general preventiva."


def check_vehicle_health(vehicle_status: str) -> str:
    """
    Evalúa el estado general del vehículo.

    Args:
        vehicle_status: Estado reportado
    """

    if "overheat" in vehicle_status.lower():
        return "Estado crítico: posible sobrecalentamiento."

    if "noise" in vehicle_status.lower():
        return "Advertencia: revisar componentes mecánicos."

    return "Estado general estable."


def get_service_recommendation(mileage: int) -> str:
    """
    Recomienda servicio basado en kilometraje.

    Args:
        mileage: Kilometraje actual
    """

    if mileage >= 40000:
        return "Servicio mayor recomendado."

    if mileage >= 20000:
        return "Servicio intermedio recomendado."

    if mileage >= 10000:
        return "Servicio básico recomendado."

    return "No se requiere servicio inmediato."


def estimate_repair_severity(problem: str) -> str:
    """
    Estima severidad del problema.

    Args:
        problem: Problema reportado
    """

    critical_keywords = [
        "engine",
        "brake",
        "transmission",
        "overheat"
    ]

    if any(
        keyword in problem.lower()
        for keyword in critical_keywords
    ):
        return "Severidad alta. Requiere atención inmediata."

    return "Severidad moderada."