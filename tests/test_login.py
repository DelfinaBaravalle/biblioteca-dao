"""Login del personal (decisión 28): la API exige sesión y las cuentas se administran."""
import pytest

from biblioteca.orm import UsuarioFila, db
from biblioteca.web import crear_app
from sesion import CLAVE_PRUEBA, USUARIO_PRUEBA, iniciar_sesion


@pytest.fixture
def app(tmp_path):
    aplicacion = crear_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "login.db")})
    yield aplicacion
    with aplicacion.app_context():
        db.session.remove()
        db.engine.dispose()


def test_sin_sesion_la_api_responde_401(app):
    cliente = app.test_client()
    assert cliente.get("/api/estado").status_code == 401
    assert cliente.post("/api/sedes", json={"nombre": "Centro", "direccion": "C 1", "contacto": "1",
                                           "horarios": "8 a 18"}).status_code == 401
    assert cliente.get("/api/reportes/movimientos/pdf").status_code == 401
    # La página en sí se sirve: es la que muestra el formulario de ingreso.
    assert cliente.get("/").status_code == 200


def test_primer_usuario_solo_con_la_base_vacia(app):
    cliente = app.test_client()
    assert cliente.get("/api/sesion").json == {"usuario": None, "sin_usuarios": True}
    iniciar_sesion(cliente)
    assert cliente.get("/api/sesion").json["usuario"] == USUARIO_PRUEBA
    otro = app.test_client()
    respuesta = otro.post("/api/usuarios/primero", json={"usuario": "intruso", "nombre": "X", "clave": "12345678"})
    assert respuesta.status_code == 403
    assert otro.get("/api/sesion").json == {"usuario": None, "sin_usuarios": False}


def test_login_incorrecto_y_logout(app):
    cliente = iniciar_sesion(app.test_client())
    cliente.post("/api/logout")
    assert cliente.get("/api/estado").status_code == 401
    malo = cliente.post("/api/login", json={"usuario": USUARIO_PRUEBA, "clave": "otra-clave"})
    assert (malo.status_code, malo.json["error"]) == (401, "Usuario o contraseña incorrectos.")
    assert cliente.post("/api/login", json={"usuario": "nadie", "clave": CLAVE_PRUEBA}).json == malo.json
    assert cliente.post("/api/login", json={"usuario": USUARIO_PRUEBA.upper(), "clave": CLAVE_PRUEBA}).status_code == 200


def test_la_contrasena_no_se_guarda_ni_se_devuelve(app):
    cliente = iniciar_sesion(app.test_client())
    alta = cliente.post("/api/usuarios", json={"usuario": "ana", "nombre": "Ana Pérez", "clave": "secreta-123"})
    assert alta.status_code == 201
    assert set(alta.json) == {"id", "usuario", "nombre", "activo"}
    with app.app_context():
        fila = db.session.scalar(db.select(UsuarioFila).filter_by(usuario="ana"))
        assert fila.clave_hash != "secreta-123" and "secreta-123" not in fila.clave_hash


def test_validaciones_del_alta(app):
    cliente = iniciar_sesion(app.test_client())
    corta = cliente.post("/api/usuarios", json={"usuario": "ana", "nombre": "Ana", "clave": "corta"})
    assert corta.status_code == 400
    con_espacio = cliente.post("/api/usuarios", json={"usuario": "ana p", "nombre": "Ana", "clave": "12345678"})
    assert con_espacio.status_code == 400
    repetido = cliente.post("/api/usuarios", json={"usuario": USUARIO_PRUEBA, "nombre": "Otro", "clave": "12345678"})
    assert (repetido.status_code, repetido.json["error"]) == (400, "Ya existe ese usuario.")


def test_desactivar_corta_el_acceso_y_no_se_puede_a_uno_mismo(app):
    admin = iniciar_sesion(app.test_client())
    ana = admin.post("/api/usuarios", json={"usuario": "ana", "nombre": "Ana", "clave": "secreta-123"}).json
    cliente_ana = app.test_client()
    assert cliente_ana.post("/api/login", json={"usuario": "ana", "clave": "secreta-123"}).status_code == 200
    assert admin.post(f"/api/usuarios/{ana['id']}/desactivar").json["activo"] is False
    # La sesión que ya estaba abierta deja de servir, y no puede volver a entrar.
    assert cliente_ana.get("/api/estado").status_code == 401
    assert cliente_ana.post("/api/login", json={"usuario": "ana", "clave": "secreta-123"}).status_code == 401
    propio = admin.get("/api/sesion").json["id"]
    assert admin.post(f"/api/usuarios/{propio}/desactivar").status_code == 400
    assert admin.post(f"/api/usuarios/{ana['id']}/activar").json["activo"] is True
    assert cliente_ana.post("/api/login", json={"usuario": "ana", "clave": "secreta-123"}).status_code == 200
