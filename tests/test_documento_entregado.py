"""Verificación final contra DISENO_ENTREGADO.md: asociaciones, Vista 4, patrones y reglas principales."""
from datetime import date, timedelta
import inspect

import pytest

from biblioteca import estados_remito, observadores, reportes
from biblioteca.modelos import Remito
from biblioteca.observadores import HistorialRemito
from biblioteca.orm import FILAS, HistorialFila
from biblioteca.sistema import Biblioteca


# --- Diagrama general: cada asociación tiene su clave foránea (o referencia) ---

# (tabla, columna, tabla referenciada, admite nulo) según la tabla del diagrama general.
ASOCIACIONES = [
    ("ejemplares", "sede_id", "sedes", False),        # Sede 1 — 0..* Ejemplar «propietaria»
    ("ejemplares", "ubicacion_id", "sedes", True),    # Sede 0..1 — 0..* Ejemplar «ubicación registrada»
    ("reservas", "sede_id", "sedes", False),          # Sede — Reserva «retiro»
    ("solicitudes", "origen_id", "sedes", False),     # Sede — Solicitud «origen / destino»
    ("solicitudes", "destino_id", "sedes", False),
    ("prestamos", "origen_id", "sedes", False),       # Sede — Prestamo «origen / destino»
    ("prestamos", "destino_id", "sedes", False),
    ("devoluciones", "sede_id", "sedes", False),      # Sede — Devolucion «receptora»
    ("remitos", "origen_id", "sedes", False),         # Sede — Remito «origen / destino»
    ("remitos", "destino_id", "sedes", False),
    ("ejemplares", "libro_id", "libros", False),      # Libro — Ejemplar «tiene»
    ("reservas", "libro_id", "libros", False),        # Libro — Reserva
    ("solicitudes", "libro_id", "libros", False),     # Libro — Solicitud
    ("solicitudes", "socio_id", "socios", False),     # Socio — Solicitud «pide»
    ("reservas", "socio_id", "socios", False),        # Socio — Reserva «reserva»
    ("prestamos", "socio_id", "socios", False),       # Socio — Prestamo
    ("prestamos", "ejemplar_id", "ejemplares", False),    # Ejemplar — Prestamo «es prestado en»
    ("remitos", "ejemplar_id", "ejemplares", False),      # Ejemplar — Remito «traslada»
    ("reparaciones", "ejemplar_id", "ejemplares", False), # Ejemplar — Reparacion
    ("solicitudes", "prestamo_id", "prestamos", True),    # Solicitud 0..1 — 0..1 Prestamo «genera»
    ("entregas", "prestamo_id", "prestamos", False),      # Prestamo 1 — 0..1 Entrega
    ("devoluciones", "prestamo_id", "prestamos", False),  # Prestamo 1 — 0..1 Devolucion
    ("remitos", "prestamo_id", "prestamos", False),       # Prestamo 1 — 0..2 Remito «ida / retorno»
] + [(tabla, "estado_id", "estados", False)               # Estado 1 — 0..* entidades
     for tabla in ("ejemplares", "prestamos", "solicitudes", "reservas", "reparaciones")]


@pytest.mark.parametrize("tabla, columna, referida, nula", ASOCIACIONES)
def test_cada_asociacion_tiene_su_clave_foranea(tabla, columna, referida, nula):
    columna_orm = FILAS[tabla].__table__.columns[columna]
    assert [fk.column.table.name for fk in columna_orm.foreign_keys] == [referida]
    assert columna_orm.nullable == nula


def test_multiplicidades_0_1_de_entrega_y_devolucion():
    for tabla in ("entregas", "devoluciones"):
        assert FILAS[tabla].__table__.columns["prestamo_id"].unique


def test_remito_crea_y_contiene_su_historial():
    remito = Remito(1, 1, 1, 1, 2, "ida")
    assert isinstance(remito._registro, HistorialRemito)
    assert remito._registro in remito._observadores
    assert [fk.column.table.name for fk in HistorialFila.__table__.columns["remito_id"].foreign_keys] == ["remitos"]


def test_un_prestamo_genera_como_maximo_dos_remitos():
    b = Biblioteca()
    for nombre in ("Centro", "Norte"):
        b.agregar_sede(nombre, "Calle 1", "111", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_libro("978-1", "Libro", "Autora")
    b.agregar_ejemplar("E1", 1, 1)
    b.prestar(1, 1, 1, 2)
    for accion in ("empaquetar", "despachar"):
        b.avanzar_remito(1, accion)
    b.avanzar_remito(1, "recibir", condicion="bueno")
    b.entregar(1)
    b.devolver(1, "bueno")
    for accion in ("empaquetar", "despachar"):
        b.avanzar_remito(2, accion)
    b.avanzar_remito(2, "recibir", condicion="bueno")
    assert [(r.tipo, r.prestamo_id) for r in b.remitos] == [("ida", 1), ("retorno", 1)]
    assert b.prestamos[0].estado.es("devuelto")
    # El préstamo cerrado no admite otra devolución ni otra entrega: no puede nacer un tercer remito.
    with pytest.raises(ValueError):
        b.devolver(1, "bueno")
    with pytest.raises(ValueError):
        b.entregar(1)
    assert len(b.remitos) == 2


def test_un_prestamo_local_no_genera_remitos():
    b = Biblioteca()
    b.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_libro("978-1", "Libro", "Autora")
    b.agregar_ejemplar("E1", 1, 1)
    b.prestar(1, 1, 1, 1)
    b.entregar(1)
    b.devolver(1, "bueno")
    assert b.prestamos[0].estado.es("devuelto") and b.remitos == []


# --- Vista 4 y clases de los patrones ---

def test_biblioteca_de_la_vista_4():
    b = Biblioteca()
    for coleccion in ("sedes", "socios", "libros", "ejemplares", "solicitudes", "prestamos", "reservas",
                      "remitos", "entregas", "devoluciones", "reparaciones"):
        assert getattr(b, coleccion) == []
    assert Biblioteca.DIAS_PRESTAMO == 14
    assert isinstance(Biblioteca.MULTA_DIARIA, float)


def test_clases_de_state():
    assert inspect.isabstract(estados_remito.EstadoRemito)
    concretos = [c.__name__ for c in estados_remito.EstadoRemito.__subclasses__()]
    assert concretos == ["Pendiente", "Empaquetado", "Despachado", "Recibido", "Extraviado", "Cancelado"]
    for clase in estados_remito.EstadoRemito.__subclasses__():
        assert list(inspect.signature(clase.avanzar).parameters) == ["self", "accion"]
        assert isinstance(clase.nombre, str)
    assert list(inspect.signature(Remito.avanzar).parameters) == ["self", "accion", "observacion"]


def test_clases_de_observer():
    assert inspect.isabstract(observadores.ObservadorRemito)
    assert list(inspect.signature(observadores.ObservadorRemito.actualizar).parameters) == [
        "self", "remito", "observacion"]
    historial = HistorialRemito()
    assert historial._cambios == []
    for metodo in ("actualizar", "agregar", "consultar"):
        assert callable(getattr(historial, metodo))


def test_clases_de_strategy():
    assert inspect.isabstract(reportes.Reporte)
    generador = reportes.GeneradorReportes()
    assert hasattr(generador, "reporte")
    for metodo in ("establecer_reporte", "generar"):
        assert callable(getattr(generador, metodo))
    tipos = {reportes.PrestamosActivos: dict, reportes.Disponibilidad: dict,
             reportes.MasSolicitados: list, reportes.Movimientos: list}
    for clase, tipo in tipos.items():
        generador.establecer_reporte(clase())
        assert isinstance(generador.generar(Biblioteca()), tipo)


# --- Reglas principales (Alcances) ---

def crear_biblioteca():
    b = Biblioteca()
    b.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    b.agregar_sede("Norte", "Calle 2", "222", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_socio("456", "Luis", "luis@mail")
    b.agregar_libro("978-1", "Libro", "Autora")
    b.agregar_ejemplar("E1", 1, 1)
    b.agregar_ejemplar("E2", 1, 1)
    return b


def test_regla_14_dias_desde_la_entrega_y_recibir_no_es_entregar():
    b = crear_biblioteca()
    p = b.prestar(1, 1, 1, 2)
    for accion in ("empaquetar", "despachar"):
        b.avanzar_remito(1, accion)
    b.avanzar_remito(1, "recibir", condicion="bueno")
    assert p.estado.es("listo_retiro") and p.inicio is None and p.vencimiento is None
    b.entregar(p.id)
    assert p.vencimiento == date.today() + timedelta(days=14)


def test_regla_multa_por_dia_con_tarifa_configurable():
    b = crear_biblioteca()
    p = b.prestar(1, 1, 1, 1)
    b.entregar(p.id)
    p.vencimiento = date.today() - timedelta(days=2)
    assert p.multa(b.MULTA_DIARIA) == 2 * 500.0
    assert p.multa(300.0) == 600.0


def test_regla_socio_habilitado_y_sin_prestamos_vencidos():
    b = crear_biblioteca()
    b.cambiar_socio(2, False)
    with pytest.raises(ValueError):
        b.prestar(2, 1, 1, 1)
    p = b.prestar(1, 1, 1, 1)
    b.entregar(p.id)
    p.vencimiento = date.today() - timedelta(days=1)
    with pytest.raises(ValueError):
        b.prestar(1, 2, 1, 1)


def test_regla_ejemplar_disponible_en_buen_estado_y_de_la_sede_de_origen():
    b = crear_biblioteca()
    with pytest.raises(ValueError):
        b.prestar(1, 1, 2, 2)          # No pertenece a la sede de origen.
    b.cambiar_condicion(2, "dañado")
    with pytest.raises(ValueError):
        b.prestar(1, 2, 1, 1)          # No está en buen estado.
    b.prestar(1, 1, 1, 1)
    with pytest.raises(ValueError):
        b.prestar(2, 1, 1, 1)          # Ya no está disponible.


def test_regla_sedes_activas():
    b = crear_biblioteca()
    b.cambiar_sede(2, False)
    with pytest.raises(ValueError):
        b.prestar(1, 1, 1, 2)
    with pytest.raises(ValueError):
        b.reservar(1, 1, 2)


def test_regla_rechazo_de_duplicados():
    b = crear_biblioteca()
    for alta in (lambda: b.agregar_socio("0123", "Otra", "x@mail"),
                 lambda: b.agregar_libro("978 1", "Otro", "Otra"),
                 lambda: b.agregar_ejemplar("e1", 1, 1),
                 lambda: b.agregar_sede("centro", "Calle 9", "999", "8 a 18")):
        with pytest.raises(ValueError):
            alta()


def test_regla_conservacion_de_historiales():
    b = crear_biblioteca()
    b.prestar(1, 1, 1, 2)
    b.avanzar_remito(1, "empaquetar", "Caja 1")
    b.avanzar_remito(1, "despachar")
    b.avanzar_remito(1, "informar_extravio", "No llegó")
    historial = b.remitos[0].consultar_historial()
    assert [h["estado"] for h in historial] == ["pendiente", "empaquetado", "despachado", "extraviado"]
    historial.clear()
    assert len(b.remitos[0].consultar_historial()) == 4
