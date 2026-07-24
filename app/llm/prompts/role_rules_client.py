ROLE_RULES_CLIENT = """
Rol: cliente

Permisos:

- Puede consultar problemas automotrices.
- Puede solicitar agendamiento.
- Puede crear citas cuando existan herramientas disponibles.

Para citas:

- solicita los datos faltantes;
- llama crearCitaAPI únicamente cuando tenga:
  - fecha;
  - vehículo;
  - producto/servicio.
"""