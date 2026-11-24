"""Clase Estado (Vista 3): catálogo por ámbito, es(), es_ambito() y control de ámbito."""
import sqlite3
from contextlib import closing

import pytest

from biblioteca.estados import Estado, ESTADOS, obtener_estado, id_estado
from biblioteca.modelos import Ejemplar, Prestamo, Reserva, Solicitud, Reparacion
from biblioteca.orm import db, EstadoFila, cargar_estados
from biblioteca.sistema import Biblioteca
from sesion import iniciar_sesion
from biblioteca.web import crear_app


# Transcripción literal de "Estados por ámbito" del documento entregado.
ESTADOS_DEL_DOCUMENTO = {
    "Ejemplar": ["disponible", "comprometido", "prestado", "en_transito",
                 "fuera_servicio", "en_reparacion", "extraviado"],
    "Prestamo": ["esperando_envio", "listo_retiro", "activo", "retornando", "devuelto", "cancelado"],
    "Solicitud": ["pendiente", "asignada", "cancelada"],
    "Reserva": ["pendiente", "atendida", "cancelada"],
    "Reparacion": ["abierta", "cerrada"],
}


def test_catalogo_coincide_con_el_documento():
    por_ambito = {}
    for estado in ESTADOS:
        por_ambito.setdefault(estado.ambito, []).append(estado.nombre)
    assert por_ambito == ESTADOS_DEL_DOCUMENTO
    assert [estado.id for estado in ESTADOS] == list(range(1, len(ESTADOS) + 1))


def test_es_y_es_ambito():
    estado = Estado(1, "disponible", "Ejemplar")
    assert estado.es("disponible")
    assert not estado.es("prestado")
    assert estado.es_ambito("Ejemplar")
    assert not estado.es_ambito("Prestamo")


def test_busqueda_por_ambito_y_estado_inexistente():
    # "pendiente" existe en Solicitud y en Reserva, pero son estados distintos.
    assert id_estado("Solicitud", "pendiente") != id_estado("Reserva", "pendiente")
    assert obtener_estado(id_estado("Reserva", "pendiente")).es_ambito("Reserva")
    with pytest.raises(ValueError):
        id_estado("Ejemplar", "activo")
    with pytest.raises(ValueError):
        obtener_estado(999)


def crear_entidades():
    return {"Ejemplar": Ejemplar(1, "E1", 1, 1, 1),
            "Prestamo": Prestamo(1, 1, 1, 1, 2, "2026-11-01", id_estado("Prestamo", "esperando_envio")),
            "Solicitud": Solicitud(1, 1, 1, 1, 2, "2026-11-01"),
            "Reserva": Reserva(1, 1, 1, 1, "2026-11-01"),
            "Reparacion": Reparacion(1, 1, "Lomo despegado", "2026-11-01")}


@pytest.mark.parametrize("ambito", list(ESTADOS_DEL_DOCUMENTO))
def test_cada_entidad_rechaza_estados_de_otro_ambito(ambito):
    entidad = crear_entidades()[ambito]
    anterior = entidad.estado_id
    assert entidad.estado.es_ambito(ambito)
    for estado in ESTADOS:
        if not estado.es_ambito(ambito):
            with pytest.raises(ValueError):
                entidad.estado_id = estado.id
            assert entidad.estado_id == anterior


def test_constructor_rechaza_estado_de_otro_ambito():
    with pytest.raises(ValueError):
        Ejemplar(1, "E1", 1, 1, 1, id_estado("Prestamo", "activo"))


def test_estados_iniciales():
    entidades = crear_entidades()
    assert entidades["Ejemplar"].estado.es("disponible")
    assert entidades["Prestamo"].estado.es("esperando_envio")
    assert entidades["Solicitud"].estado.es("pendiente")
    assert entidades["Reserva"].estado.es("pendiente")
    assert entidades["Reparacion"].estado.es("abierta")


def test_biblioteca_tiene_los_estados():
    sistema = Biblioteca()
    assert [e.a_fila() for e in sistema.estados] == [e.a_fila() for e in ESTADOS]
    assert "estados" not in sistema.colecciones()


def contar_estados(ruta):
    with closing(sqlite3.connect(ruta)) as conexion:
        return conexion.execute("SELECT COUNT(*) FROM estados").fetchone()[0]


def test_tabla_de_estados_se_carga_una_sola_vez(tmp_path):
    ruta = tmp_path / "estados.db"
    configuracion = {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(ruta)}
    for _ in range(2):
        app = crear_app(configuracion)
        with app.app_context():
            cargar_estados()
            filas = db.session.scalars(db.select(EstadoFila).order_by(EstadoFila.id)).all()
            assert [(f.id, f.nombre, f.ambito) for f in filas] == [e.a_fila() for e in ESTADOS]
            db.session.remove()
            db.engine.dispose()
    assert contar_estados(ruta) == len(ESTADOS)


def test_tabla_de_estados_distinta_se_rechaza(tmp_path):
    app = crear_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "e.db")})
    with app.app_context():
        db.session.get(EstadoFila, 1).nombre = "otro"
        db.session.commit()
        with pytest.raises(ValueError):
            cargar_estados()
        db.session.remove()
        db.engine.dispose()


def test_api_devuelve_estado_id_y_nombre(tmp_path):
    app = crear_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "api.db")})
    cliente = iniciar_sesion(app.test_client())
    cliente.post("/api/sedes", json={"nombre": "Centro", "direccion": "Calle 1",
                                     "contacto": "111", "horarios": "8 a 18"})
    cliente.post("/api/libros", json={"isbn": "9781", "titulo": "Libro", "autor": "Autor"})
    ejemplar = cliente.post("/api/ejemplares", json={"codigo": "E1", "libro_id": 1, "sede_id": 1}).json
    assert ejemplar["estado"] == "disponible"
    assert ejemplar["estado_id"] == id_estado("Ejemplar", "disponible")
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def test_persistencia_guarda_estado_id(recargar):
    sistema = Biblioteca()
    sistema.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    sistema.agregar_libro("9781", "Libro", "Autor")
    sistema.agregar_ejemplar("E1", 1, 1)
    sistema.cambiar_condicion(1, "dañado")
    copia = recargar(sistema)
    assert copia.ejemplares[0].estado.es("fuera_servicio")
    assert copia.ejemplares[0].estado_id == id_estado("Ejemplar", "fuera_servicio")
