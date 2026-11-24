"""Las clases de dominio tienen los atributos, métodos y tipos de las Vistas 1 y 2 del documento."""
import inspect
from datetime import date, datetime

import pytest

from biblioteca import modelos
from biblioteca.estados import id_estado
from biblioteca.sistema import Biblioteca


# Atributos de las Vistas 1 y 2, en el orden del documento entregado.
ATRIBUTOS = {
    "Libro": ["id", "isbn", "titulo", "autor"],
    "Socio": ["id", "dni", "nombre", "contacto", "habilitado"],
    "Sede": ["id", "nombre", "direccion", "contacto", "horarios", "activa"],
    "Ejemplar": ["id", "codigo", "libro_id", "sede_id", "ubicacion_id", "estado_id", "condicion"],
    "Reserva": ["id", "socio_id", "libro_id", "sede_id", "fecha", "estado_id"],
    "Solicitud": ["id", "socio_id", "libro_id", "origen_id", "destino_id", "fecha", "estado_id",
                  "prestamo_id"],
    "Prestamo": ["id", "socio_id", "ejemplar_id", "origen_id", "destino_id", "fecha_solicitud",
                 "estado_id", "inicio", "vencimiento"],
    "Entrega": ["id", "prestamo_id", "fecha"],
    "Devolucion": ["id", "prestamo_id", "sede_id", "fecha", "condicion"],
    "Reparacion": ["id", "ejemplar_id", "descripcion", "inicio", "fin", "estado_id", "resultado"],
}

# Métodos de las Vistas 1 y 2 con sus parámetros. None indica una propiedad.
# multa suma fecha_corte, opcional (decisión 4 del README).
METODOS = {
    "Socio": {"verificar_habilitado": []},
    "Sede": {"verificar_activa": []},
    "Ejemplar": {"esta_disponible": ["sede_id"], "cambiar_condicion": ["condicion"]},
    "Reserva": {"cancelar": []},
    "Prestamo": {"vencido": None, "activar": ["dias"], "dias_atraso": ["fecha_corte"],
                 "multa": ["tarifa_diaria", "fecha_corte"]},
    "Remito": {"estado": None, "avanzar": ["accion", "observacion"], "suscribir": ["observador"],
               "desuscribir": ["observador"], "notificar": ["observacion"], "consultar_historial": []},
}


@pytest.mark.parametrize("clase, atributos", ATRIBUTOS.items())
def test_atributos_del_documento(clase, atributos):
    objeto = crear_objetos()[clase]
    parametros = list(inspect.signature(type(objeto).__init__).parameters)[1:]
    assert set(parametros) == set(atributos)
    for atributo in atributos:
        assert hasattr(objeto, atributo)
    # Se guarda un valor por atributo: no quedan columnas fuera del documento.
    assert len(objeto.a_fila()) == len(atributos)


@pytest.mark.parametrize("clase, metodos", METODOS.items())
def test_metodos_del_documento(clase, metodos):
    for metodo, parametros in metodos.items():
        miembro = getattr(getattr(modelos, clase), metodo)
        if parametros is None:
            assert isinstance(miembro, property), metodo
        else:
            assert list(inspect.signature(miembro).parameters)[1:] == parametros, metodo


def test_no_quedan_atributos_ni_metodos_retirados():
    p = crear_objetos()["Prestamo"]
    for nombre in ("solicitud", "devolucion", "condicion_devolucion", "registrar_devolucion"):
        assert not hasattr(p, nombre)
    assert not hasattr(crear_objetos()["Entrega"], "tipo")
    assert not hasattr(modelos.Ejemplar, "liberar")
    assert not hasattr(modelos.Remito, "registrar_creacion")


def test_remito_atributos_de_la_vista_2():
    remito = modelos.Remito(1, 1, 1, 1, 2, "ida")
    for nombre in ("id", "prestamo_id", "ejemplar_id", "origen_id", "destino_id", "tipo",
                   "condicion_recepcion", "_estado", "_observadores"):
        assert hasattr(remito, nombre)


def crear_objetos():
    b = Biblioteca()
    b.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_libro("978-1", "Libro", "Autora")
    b.agregar_ejemplar("E1", 1, 1)
    b.agregar_ejemplar("E2", 1, 1)
    b.cambiar_condicion(2, "dañado")
    reserva = b.reservar(1, 1, 1)
    solicitud = b.solicitar(1, 1, 1, 1)
    b.asignar_solicitud(solicitud.id, 1)
    prestamo = b.prestamos[0]
    b.entregar(prestamo.id)
    b.devolver(prestamo.id, "bueno")
    reparacion = b.iniciar_reparacion(2, "Lomo despegado")
    return {"Libro": b.libros[0], "Socio": b.socios[0], "Sede": b.sedes[0],
            "Ejemplar": b.ejemplares[0], "Reserva": reserva, "Solicitud": solicitud,
            "Prestamo": prestamo, "Entrega": b.entregas[0], "Devolucion": b.devoluciones[0],
            "Reparacion": reparacion}


def test_tipos_de_fechas_del_documento():
    o = crear_objetos()
    p = o["Prestamo"]
    assert type(p.fecha_solicitud) is date
    assert isinstance(p.inicio, datetime)
    assert type(p.vencimiento) is date
    assert isinstance(o["Reserva"].fecha, datetime)
    assert isinstance(o["Solicitud"].fecha, datetime)
    assert isinstance(o["Entrega"].fecha, datetime)
    assert isinstance(o["Devolucion"].fecha, datetime)
    assert isinstance(o["Reparacion"].inicio, datetime)
    assert o["Reparacion"].fin is None


def test_valores_vacios_son_none_y_la_base_recibe_texto():
    esperando = id_estado("Prestamo", "esperando_envio")
    p = modelos.Prestamo(1, 1, 1, 1, 2, "2026-11-01", esperando)
    assert p.inicio is None and p.vencimiento is None
    assert p.a_fila()[5:] == ("2026-11-01", esperando, None, None)
    reparacion = modelos.Reparacion(1, 1, "Lomo", "2026-11-01T10:00:00")
    assert reparacion.fin is None
    assert reparacion.a_fila()[3] == "2026-11-01T10:00:00"
