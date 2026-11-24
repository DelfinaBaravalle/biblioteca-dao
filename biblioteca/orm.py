"""Filas persistentes. El negocio y los patrones permanecen en las entidades del dominio."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .sistema import Biblioteca
from .estados import ESTADOS

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def activar_claves_foraneas(conexion, registro):
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


class EstadoFila(db.Model):
    __tablename__ = "estados"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    ambito = db.Column(db.String, nullable=False)
    __table_args__ = (db.UniqueConstraint("nombre", "ambito"),)


class SedeFila(db.Model):
    __tablename__ = "sedes"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(collation="NOCASE"), nullable=False, unique=True)
    direccion = db.Column(db.String, nullable=False)
    contacto = db.Column(db.String, nullable=False)
    horarios = db.Column(db.String, nullable=False)
    activa = db.Column(db.Boolean, nullable=False)


class SocioFila(db.Model):
    __tablename__ = "socios"
    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String, nullable=False, unique=True)
    nombre = db.Column(db.String, nullable=False)
    contacto = db.Column(db.String, nullable=False)
    habilitado = db.Column(db.Boolean, nullable=False)


class LibroFila(db.Model):
    __tablename__ = "libros"
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String, nullable=False, unique=True)
    titulo = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)


class EjemplarFila(db.Model):
    __tablename__ = "ejemplares"
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(collation="NOCASE"), nullable=False, unique=True)
    libro_id = db.Column(db.Integer, db.ForeignKey("libros.id"), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey("sedes.id"))
    estado_id = db.Column(db.Integer, db.ForeignKey("estados.id"), nullable=False)
    condicion = db.Column(db.String, nullable=False)
    __table_args__ = (db.CheckConstraint("condicion IN ('bueno','dañado','inutilizable')"),)


class PrestamoFila(db.Model):
    __tablename__ = "prestamos"
    id = db.Column(db.Integer, primary_key=True)
    socio_id = db.Column(db.Integer, db.ForeignKey("socios.id"), nullable=False)
    ejemplar_id = db.Column(db.Integer, db.ForeignKey("ejemplares.id"), nullable=False)
    origen_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    destino_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    fecha_solicitud = db.Column(db.String, nullable=False)
    estado_id = db.Column(db.Integer, db.ForeignKey("estados.id"), nullable=False)
    inicio = db.Column(db.String)
    vencimiento = db.Column(db.String)


class ReservaFila(db.Model):
    __tablename__ = "reservas"
    id = db.Column(db.Integer, primary_key=True)
    socio_id = db.Column(db.Integer, db.ForeignKey("socios.id"), nullable=False)
    libro_id = db.Column(db.Integer, db.ForeignKey("libros.id"), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    fecha = db.Column(db.String, nullable=False)
    estado_id = db.Column(db.Integer, db.ForeignKey("estados.id"), nullable=False)


class RemitoFila(db.Model):
    __tablename__ = "remitos"
    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False)
    ejemplar_id = db.Column(db.Integer, db.ForeignKey("ejemplares.id"), nullable=False)
    origen_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    destino_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    estado = db.Column(db.String, nullable=False)
    condicion_recepcion = db.Column(db.String)
    __table_args__ = (
        db.CheckConstraint("tipo IN ('ida','retorno')"),
        db.CheckConstraint("estado IN ('pendiente','empaquetado','despachado',"
                           "'recibido','extraviado','cancelado')"),
        db.CheckConstraint("condicion_recepcion IS NULL OR "
                           "condicion_recepcion IN ('bueno','dañado','inutilizable')"))


class SolicitudFila(db.Model):
    __tablename__ = "solicitudes"
    id = db.Column(db.Integer, primary_key=True)
    socio_id = db.Column(db.Integer, db.ForeignKey("socios.id"), nullable=False)
    libro_id = db.Column(db.Integer, db.ForeignKey("libros.id"), nullable=False)
    origen_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    destino_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    fecha = db.Column(db.String, nullable=False)
    estado_id = db.Column(db.Integer, db.ForeignKey("estados.id"), nullable=False)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"))


class DevolucionFila(db.Model):
    __tablename__ = "devoluciones"
    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False, unique=True)
    sede_id = db.Column(db.Integer, db.ForeignKey("sedes.id"), nullable=False)
    fecha = db.Column(db.String, nullable=False)
    condicion = db.Column(db.String, nullable=False)


class ReparacionFila(db.Model):
    __tablename__ = "reparaciones"
    id = db.Column(db.Integer, primary_key=True)
    ejemplar_id = db.Column(db.Integer, db.ForeignKey("ejemplares.id"), nullable=False)
    descripcion = db.Column(db.String, nullable=False)
    inicio = db.Column(db.String, nullable=False)
    estado_id = db.Column(db.Integer, db.ForeignKey("estados.id"), nullable=False)
    fin = db.Column(db.String)
    resultado = db.Column(db.String, nullable=False)


class EntregaFila(db.Model):
    __tablename__ = "entregas"
    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False, unique=True)
    fecha = db.Column(db.String, nullable=False)
    prestamo = db.relationship(PrestamoFila, backref=db.backref("registro_entrega", uselist=False))


class HistorialFila(db.Model):
    __tablename__ = "historial_remitos"
    remito_id = db.Column(db.Integer, db.ForeignKey("remitos.id"), primary_key=True)
    orden = db.Column(db.Integer, primary_key=True)
    estado = db.Column(db.String, nullable=False)
    fecha = db.Column(db.String, nullable=False)
    observacion = db.Column(db.String, nullable=False)


class UsuarioFila(db.Model):
    """Cuenta del personal (decisión 28). No es una entidad del dominio: no está en FILAS."""
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String, nullable=False, unique=True)
    nombre = db.Column(db.String, nullable=False)
    clave_hash = db.Column(db.String, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)


FILAS = {"sedes": SedeFila, "socios": SocioFila, "libros": LibroFila,
         "ejemplares": EjemplarFila, "prestamos": PrestamoFila, "reservas": ReservaFila,
         "remitos": RemitoFila, "solicitudes": SolicitudFila,
         "devoluciones": DevolucionFila, "reparaciones": ReparacionFila, "entregas": EntregaFila}


def serializar(objeto, coleccion, sistema):
    campos = [c.name for c in FILAS[coleccion].__table__.columns]
    datos = dict(zip(campos, objeto.a_fila()))
    if "estado_id" in datos:
        # La API conserva el nombre del estado para que el front no cambie de formato.
        datos["estado"] = objeto.estado.nombre
    if coleccion == "remitos":
        datos["historial"] = objeto.consultar_historial()
    if coleccion == "prestamos":
        datos["vencido"] = objeto.vencido
        # Los datos de la devolución viven en Devolucion;
        # se agregan al préstamo solo para mostrarlos en la interfaz.
        devolucion = next((d for d in sistema.devoluciones if d.prestamo_id == objeto.id), None)
        datos["devolucion"] = devolucion.fecha.isoformat() if devolucion else None
        datos["condicion_devolucion"] = devolucion.condicion if devolucion else None
    if coleccion == "reservas":
        # Se calcula al consultar, con la misma regla que usa la fila FIFO (decisión 26).
        prestamo = sistema._prestamo_en_curso(objeto) if objeto.estado.es("pendiente") else None
        datos["prestamo_en_curso"] = prestamo.id if prestamo else None
    return datos


def cargar_estados():
    """Carga una sola vez los estados del catálogo y controla que coincidan."""
    for estado in ESTADOS:
        fila = db.session.get(EstadoFila, estado.id)
        if fila is None:
            db.session.add(EstadoFila(id=estado.id, nombre=estado.nombre, ambito=estado.ambito))
        elif (fila.nombre, fila.ambito) != (estado.nombre, estado.ambito):
            raise ValueError("La tabla de estados no coincide con el catálogo.")
    db.session.commit()


def cargar_dominio():
    sistema = Biblioteca()
    for nombre, fila in FILAS.items():
        campos = [c.name for c in fila.__table__.columns]
        registros = db.session.scalars(db.select(fila).order_by(fila.id)).all()
        for registro in registros:
            sistema.colecciones()[nombre].append(
                sistema.TIPOS[nombre](*(getattr(registro, c) for c in campos)))
    for cambio in db.session.scalars(db.select(HistorialFila).order_by(
            HistorialFila.remito_id, HistorialFila.orden)):
        sistema.buscar("remitos", cambio.remito_id).recuperar_cambio(
            cambio.estado, cambio.fecha, cambio.observacion)
    return sistema


def guardar_dominio(sistema):
    """Actualiza filas e incorpora altas. No elimina registros ni reescribe el historial."""
    for nombre, fila in FILAS.items():
        campos = [c.name for c in fila.__table__.columns]
        for objeto in sistema.colecciones()[nombre]:
            registro = db.session.get(fila, objeto.id)
            if registro is None:
                registro = fila(id=objeto.id)
                db.session.add(registro)
            for campo, valor in zip(campos, objeto.a_fila()):
                setattr(registro, campo, valor)
        db.session.flush()
    for remito in sistema.remitos:
        for orden, cambio in enumerate(remito.consultar_historial()):
            if db.session.get(HistorialFila, (remito.id, orden)) is None:
                db.session.add(HistorialFila(remito_id=remito.id, orden=orden, **cambio))
    db.session.flush()
