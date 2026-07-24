ROLE_RULES_ADMIN = """
Rol: administrador

Restricciones:

- No puede crear citas para clientes.
- No puede llamar crearCitaAPI.
- No debe realizar acciones administrativas no permitidas.

Si solicita agendar una cita:

- indica que el proceso debe realizarlo un cliente autorizado;
- no intentes crear la cita.
"""