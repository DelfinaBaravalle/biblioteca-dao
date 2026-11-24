"""Inicio de sesión para las pruebas de la API (decisión 28).

Las credenciales son de prueba y solo existen en las bases temporales de los tests.
"""
USUARIO_PRUEBA = "operador"
NOMBRE_PRUEBA = "Operador de prueba"
CLAVE_PRUEBA = "clave-de-prueba"


def iniciar_sesion(cliente):
    """Crea la cuenta de prueba si la base no tiene usuarios e inicia sesión con ella."""
    if cliente.get("/api/sesion").json.get("sin_usuarios"):
        respuesta = cliente.post("/api/usuarios/primero", json={
            "usuario": USUARIO_PRUEBA, "nombre": NOMBRE_PRUEBA, "clave": CLAVE_PRUEBA})
        assert respuesta.status_code == 201, respuesta.json
    respuesta = cliente.post("/api/login", json={"usuario": USUARIO_PRUEBA, "clave": CLAVE_PRUEBA})
    assert respuesta.status_code == 200, respuesta.json
    return cliente
