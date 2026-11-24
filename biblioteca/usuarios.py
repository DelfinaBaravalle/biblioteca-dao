"""Cuentas del personal de la biblioteca (decisión 28).

No forman parte del modelo del dominio: son la seguridad de la aplicación web.
La contraseña nunca se guarda: se guarda su hash, generado con Werkzeug (incluido en Flask).
"""
from werkzeug.security import check_password_hash, generate_password_hash

from .orm import UsuarioFila, db

LARGO_MINIMO_CLAVE = 8


def a_json(fila):
    # El hash nunca sale del servidor.
    return {"id": fila.id, "usuario": fila.usuario, "nombre": fila.nombre, "activo": fila.activo}


def hay_usuarios():
    return db.session.query(UsuarioFila.id).first() is not None


def listar():
    return db.session.scalars(db.select(UsuarioFila).order_by(UsuarioFila.id)).all()


def crear(usuario, nombre, clave):
    usuario, nombre = usuario.strip().lower(), nombre.strip()
    if not usuario or " " in usuario:
        raise ValueError("Ingrese un nombre de usuario sin espacios.")
    if not nombre:
        raise ValueError("Ingrese el nombre de la persona.")
    if len(clave) < LARGO_MINIMO_CLAVE:
        raise ValueError(f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres.")
    if db.session.scalar(db.select(UsuarioFila).filter_by(usuario=usuario)) is not None:
        raise ValueError("Ya existe ese usuario.")
    fila = UsuarioFila(usuario=usuario, nombre=nombre, clave_hash=generate_password_hash(clave), activo=True)
    db.session.add(fila)
    db.session.flush()
    return fila


def autenticar(usuario, clave):
    """Devuelve la cuenta si el usuario existe, está activo y la contraseña coincide."""
    fila = db.session.scalar(db.select(UsuarioFila).filter_by(usuario=usuario.strip().lower()))
    if fila is None or not fila.activo or not check_password_hash(fila.clave_hash, clave):
        return None
    return fila


def cambiar_activo(usuario_id, activo, quien_id):
    fila = db.session.get(UsuarioFila, usuario_id)
    if fila is None:
        raise ValueError("El usuario no existe.")
    if not activo and fila.id == quien_id:
        # Evita que el personal se quede sin acceso por desactivar su propia cuenta.
        raise ValueError("No puede desactivar su propio usuario.")
    fila.activo = activo
    return fila
