import pandas as pd
from pathlib import Path

from app.tools.supabase_reader import (
    fetch_documentos_tecnicos,
    format_documento_row,
    is_configured as supabase_tools_enabled,
    split_car_name,
)

# CSV empaquetados bajo app/datasets (independiente del cwd al arrancar uvicorn)
BASE_DATASET_PATH = Path(__file__).resolve().parent.parent / "datasets"


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
    Supabase documentos_tecnicos primero; CSV local como respaldo.
    """
    if supabase_tools_enabled():
        marca, modelo = split_car_name(car_name)
        rows = fetch_documentos_tecnicos(
            marca=marca,
            modelo=modelo,
            texto=problem,
            limit=3,
        )
        if rows:
            return "\n\n---\n\n".join(format_documento_row(r) for r in rows)

    matches = diagnostic_df[
        diagnostic_df["Problem Description"].str.contains(
            problem,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré diagnóstico para ese problema."

    row = matches.iloc[0]

    return (
        f"Vehículo: {row['Car Name']}\n"
        f"Clasificación: {row['Problem Classification']}\n"
        f"Problema: {row['Problem Description']}\n"
        f"Diagnóstico: {row['Diagnosis']}\n"
        f"Solución: {row['How to Fix the Problem']}\n"
        f"Severidad: {row['Severity']}\n"
        f"Estado reparación: {row['Repair Status']}\n"
        f"Resultado: {row['Results']}"
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
        return "No encontre el componente solicitado."

    row = matches.iloc[0]

    return (
        f"Componente: {row['Component']}\n"
        f"Costo: {row['Price']}"
    )




def recommend_maintenance(vehicle_issue: str) -> str:
    """
    Recomienda mantenimiento basado en sintomas.

    Args:
        vehicle_issue: Problema o sintoma detectado
    """

    if "brake" in vehicle_issue.lower():
        return "Se recomienda revision completa del sistema de frenos."

    if "battery" in vehicle_issue.lower():
        return "Se recomienda revisar bateria y sistema electrico."

    if "engine" in vehicle_issue.lower():
        return "Se recomienda diagnostico completo del motor."

    return "Se recomienda inspeccion general preventiva."


def check_vehicle_health(vehicle_status: str) -> str:
    """
    Evalua el estado general del vehiculo.

    Args:
        vehicle_status: Estado reportado
    """

    if "overheat" in vehicle_status.lower():
        return "Estado critico: posible sobrecalentamiento."

    if "noise" in vehicle_status.lower():
        return "Advertencia: revisar componentes mecanicos."

    return "Estado general estable."


def get_vehicle_service_history(car_model: str) -> str:
    """
    Consulta historial de servicios vehiculares.
    Supabase documentos_tecnicos primero; CSV local como respaldo.
    """
    if supabase_tools_enabled():
        marca, modelo = split_car_name(car_model)
        rows = fetch_documentos_tecnicos(marca=marca, modelo=modelo or car_model, limit=5)
        if not rows and car_model.strip():
            rows = fetch_documentos_tecnicos(texto=car_model, limit=5)
        if rows:
            lines = []
            for row in rows:
                hist = row.get("historial_servicio")
                block = format_documento_row(row)
                if hist:
                    block += f"\nHistorial servicio: {hist}"
                lines.append(block)
            return "\n\n---\n\n".join(lines)

    matches = service_df[
        (
            service_df["brand"].str.contains(
                car_model,
                case=False,
                na=False
            )
        )
        |
        (
            service_df["model"].str.contains(
                car_model,
                case=False,
                na=False
            )
        )
    ]

    if matches.empty:
        return "No encontré historial de servicios."

    row = matches.iloc[0]

    return (
        f"Marca: {row['brand']}\n"
        f"Modelo: {row['model']}\n"
        f"Motor: {row['engine_type']}\n"
        f"Kilometraje: {row['mileage']}\n"
        f"Costo servicio: {row['cost']}"
    )

def get_vehicle_cost_estimate(brand: str) -> str:
    """
    Estima costo de mantenimiento por marca.
    """

    matches = service_df[
        service_df["brand"].str.contains(
            brand,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré datos de costos."

    avg_cost = matches["cost"].mean()

    return (
        f"Costo promedio de mantenimiento "
        f"para {brand}: {round(avg_cost, 2)}"
    )


def detect_engine_issue(issue: str) -> str:
    """
    Detecta problemas relacionados al motor.
    """

    if "overheat" in issue.lower():
        return "Posible problema de refrigeración."

    if "noise" in issue.lower():
        return "Posible desgaste interno del motor."

    return "No se detectó falla crítica."


def recommend_oil_change(mileage: int) -> str:
    """
    Recomienda cambio de aceite.
    """

    if mileage >= 10000:
        return "Se recomienda cambio inmediato de aceite."

    return "El aceite aún está en buen estado."


def predict_component_failure(component: str) -> str:
    """
    Predice posibles fallas de componentes.
    """

    critical = [
        "battery",
        "brake",
        "engine",
        "transmission"
    ]

    if component.lower() in critical:
        return (
            f"El componente {component} "
            f"tiene alta probabilidad de desgaste."
        )

    return (
        f"No se detectan riesgos críticos "
        f"para {component}."
    )


def get_repair_status(car_name: str) -> str:
    """
    Obtiene estado de reparación.
    Supabase documentos_tecnicos primero; CSV local como respaldo.
    """
    if supabase_tools_enabled():
        marca, modelo = split_car_name(car_name)
        rows = fetch_documentos_tecnicos(marca=marca, modelo=modelo, limit=3)
        if not rows:
            rows = fetch_documentos_tecnicos(texto=car_name, limit=3)
        if rows:
            lines = []
            for row in rows:
                lines.append(
                    f"Vehículo: {row.get('vehiculo_marca', '')} {row.get('vehiculo_modelo', '')}\n"
                    f"Estado reparación: {row.get('repair_status', 'N/D')}\n"
                    f"Severidad: {row.get('severidad', 'N/D')}\n"
                    f"Problema: {row.get('problema', 'N/D')}"
                )
            return "\n\n---\n\n".join(lines)

    matches = diagnostic_df[
        diagnostic_df["Car Name"].str.contains(
            car_name,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré estado de reparación."

    row = matches.iloc[0]

    return (
        f"Vehículo: {row['Car Name']}\n"
        f"Estado reparación: {row['Repair Status']}\n"
        f"Resultado: {row['Results']}"
    )


def get_vehicle_region(model: str) -> str:
    """
    Obtiene región del vehículo.
    """

    matches = service_df[
        service_df["model"].str.contains(
            model,
            case=False,
            na=False
        )
    ]

    if matches.empty:
        return "No encontré región."

    row = matches.iloc[0]

    return (
        f"Modelo: {row['model']}\n"
        f"Región: {row['region']}"
    )


def recommend_brake_service(problem: str) -> str:
    """
    Recomienda servicio de frenos.
    """

    if "brake" in problem.lower():
        return (
            "Se recomienda revisar "
            "pastillas y líquido de frenos."
        )

    return "No se requiere servicio de frenos."


def estimate_maintenance_priority(issue: str) -> str:
    """
    Estima prioridad de mantenimiento.
    """

    critical = [
        "overheat",
        "brake",
        "engine"
    ]

    if any(
        word in issue.lower()
        for word in critical
    ):
        return "Prioridad ALTA."

    return "Prioridad MEDIA."

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
        return "Servicio basico recomendado."

    return "No se requiere servicio inmediato."


def estimate_repair_severity(problem: str) -> str:
    """
    Estima severidad del problema.
    Supabase documentos_tecnicos primero; reglas locales como respaldo.
    """
    if supabase_tools_enabled():
        rows = fetch_documentos_tecnicos(texto=problem, limit=3)
        if rows:
            lines = []
            for row in rows:
                lines.append(
                    f"Vehículo: {row.get('vehiculo_marca', '')} {row.get('vehiculo_modelo', '')}\n"
                    f"Severidad: {row.get('severidad', 'N/D')}\n"
                    f"Problema: {row.get('problema', 'N/D')}\n"
                    f"Diagnóstico: {row.get('diagnostico', 'N/D')}"
                )
            return "\n\n---\n\n".join(lines)

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
        return "Severidad alta. Requiere atencion inmediata."

    return "Severidad moderada."


def search_documentos_tecnicos(
    marca: str = "",
    modelo: str = "",
    problema: str = "",
) -> str:
    """
    Busca casos técnicos en Supabase documentos_tecnicos.
    Usar cuando el usuario pregunte por un vehículo o falla indexada en BD.
    """
    if not supabase_tools_enabled():
        return "Supabase no configurado (SUPABASE_URL / SUPABASE_SERVICE_KEY)."

    rows = fetch_documentos_tecnicos(
        marca=marca or None,
        modelo=modelo or None,
        texto=problema or None,
        limit=5,
    )
    if not rows:
        return "No encontré registros en documentos_tecnicos para esos criterios."

    return "\n\n---\n\n".join(format_documento_row(r) for r in rows)
