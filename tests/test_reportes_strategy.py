"""Reportes (Vista 4): Strategy con establecer_reporte, multas, extraviados e incidencias."""
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from biblioteca.modelos import Remito
from biblioteca.reportes import (GeneradorReportes, Reporte, PrestamosActivos, Disponibilidad,
                                 MasSolicitados, Movimientos)
from biblioteca.sistema import Biblioteca
from biblioteca.web import crear_app
from sesion import iniciar_sesion


def crear_biblioteca():
    b = Biblioteca()
    b.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    b.agregar_sede("Norte", "Calle 2", "222", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_socio("456", "Luis", "luis@mail")
    b.agregar_libro("978-1", "El principito", "Saint-Exupéry")
    b.agregar_libro("978-2", "Rayuela", "Cortázar")
    return b


# --- Contexto del patrón Strategy ---

def test_establecer_reporte_cambia_la_estrategia():
    b = crear_biblioteca()
    generador = GeneradorReportes()
    generador.establecer_reporte(Disponibilidad())
    assert isinstance(generador.reporte, Disponibilidad)
    assert isinstance(generador.generar(b), dict)
    generador.establecer_reporte(MasSolicitados())
    assert isinstance(generador.reporte, MasSolicitados)
    assert isinstance(generador.generar(b), list)


def test_generador_sin_estrategia_o_con_una_invalida():
    with pytest.raises(ValueError):
        GeneradorReportes().generar(Biblioteca())
    with pytest.raises(ValueError):
        GeneradorReportes().establecer_reporte("movimientos")
    generador = GeneradorReportes()
    generador.establecer_reporte(Movimientos())
    with pytest.raises(ValueError):
        generador.generar(Biblioteca(), "2026-12-01", "2026-01-01")


def test_los_cuatro_reportes_son_estrategias():
    for tipo in (PrestamosActivos, Disponibilidad, MasSolicitados, Movimientos):
        assert issubclass(tipo, Reporte)


def test_web_elige_la_estrategia_con_establecer_reporte(tmp_path):
    app = crear_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "r.db")})
    with patch.object(GeneradorReportes, "establecer_reporte", autospec=True,
                      side_effect=GeneradorReportes.establecer_reporte) as establecer:
        respuesta = iniciar_sesion(app.test_client()).get("/api/reportes/movimientos")
    assert respuesta.status_code == 200
    assert isinstance(establecer.call_args.args[1], Movimientos)
    with app.app_context():
        from biblioteca.orm import db
        db.session.remove()
        db.engine.dispose()


# --- Préstamos activos, vencidos y multas ---

def entregar_con_atraso(b, socio_id, ejemplar_id, dias):
    p = b.prestar(socio_id, ejemplar_id, 1, 1)
    b.entregar(p.id)
    p.vencimiento = date.today() - timedelta(days=dias)
    return p


def test_prestamos_activos_con_multas_por_prestamo_sede_y_socio():
    b = crear_biblioteca()
    for codigo, libro in (("E1", 1), ("E2", 2), ("E3", 1)):
        b.agregar_ejemplar(codigo, libro, 1)
    entregar_con_atraso(b, 1, 1, 3)              # Ana: activo y vencido, $1500 a hoy.
    devuelto = entregar_con_atraso(b, 2, 2, 2)   # Luis: devuelto con 2 días de atraso, $1000.
    b.devolver(devuelto.id, "bueno")
    b.prestar(2, 3, 1, 1)                        # Luis: listo para retirar, sin multa.
    reporte = GeneradorReportes(PrestamosActivos()).generar(b)
    detalle = {fila["prestamo"]: fila for fila in reporte["detalle"]}
    assert set(detalle) == {1, 2}
    assert detalle[1]["estado"] == "activo" and detalle[1]["devolucion"] is None
    assert (detalle[1]["dias_atraso"], detalle[1]["multa"]) == (3, 1500.0)
    assert detalle[2]["estado"] == "devuelto" and detalle[2]["devolucion"] is not None
    assert (detalle[2]["dias_atraso"], detalle[2]["multa"]) == (2, 1000.0)
    for campo in ("socio", "libro", "origen", "destino", "vencimiento"):
        assert campo in detalle[1]
    assert reporte["totales_por_sede"]["Centro"] == {"activos": 1, "vencidos": 1, "multas": 2500.0}
    assert reporte["multas_por_socio"] == [
        {"socio": "Ana", "prestamos_con_atraso": 1, "multa_total": 1500.0},
        {"socio": "Luis", "prestamos_con_atraso": 1, "multa_total": 1000.0}]
    assert "pago no se registra" in reporte["aclaracion"]


def test_devueltos_sin_atraso_y_cancelados_no_figuran():
    b = crear_biblioteca()
    b.agregar_ejemplar("E1", 1, 1)
    b.agregar_ejemplar("E2", 2, 1)
    p = b.prestar(1, 1, 1, 1)
    b.entregar(p.id)
    b.devolver(p.id, "bueno")
    b.prestar(2, 2, 1, 2)
    b.avanzar_remito(1, "cancelar")
    reporte = GeneradorReportes(PrestamosActivos()).generar(b)
    assert reporte["detalle"] == [] and reporte["multas_por_socio"] == []


def test_el_periodo_no_oculta_activos_y_filtra_devueltos_por_devolucion():
    b = crear_biblioteca()
    b.agregar_ejemplar("E1", 1, 1)
    b.agregar_ejemplar("E2", 2, 1)
    entregar_con_atraso(b, 1, 1, 3)              # Activo y vencido hoy.
    devuelto = entregar_con_atraso(b, 2, 2, 2)   # Devuelto hoy con atraso.
    b.devolver(devuelto.id, "bueno")
    generador = GeneradorReportes(PrestamosActivos())
    ayer = (date.today() - timedelta(days=1)).isoformat()
    hoy = date.today().isoformat()
    # Un período que terminó ayer: el activo sigue figurando, el devuelto hoy no.
    assert [f["prestamo"] for f in generador.generar(b, "2000-01-01", ayer)["detalle"]] == [1]
    assert [f["prestamo"] for f in generador.generar(b, hoy, hoy)["detalle"]] == [1, 2]


# --- Disponibilidad ---

def test_disponibilidad_informa_extraviados():
    b = crear_biblioteca()
    b.agregar_ejemplar("E1", 1, 1)
    b.agregar_ejemplar("E2", 1, 1)
    b.prestar(1, 1, 1, 2)
    b.avanzar_remito(1, "empaquetar")
    b.avanzar_remito(1, "despachar")
    b.avanzar_remito(1, "informar_extravio")
    fila = GeneradorReportes(Disponibilidad()).generar(b)["detalle"][0]
    assert fila["propios"] == 2 and fila["presentes"] == 1
    assert fila["propios_extraviados"] == 1 and fila["disponibles_para_prestar"] == 1
    categorias = [c for c in fila if c.startswith("propios_")]
    assert sum(fila[c] for c in categorias) == fila["propios"]


# --- Movimientos e incidencias ---

def remito(numero, estado, condicion=None):
    r = Remito(numero, numero, 1, 1, 2, "ida", estado, condicion)
    r.recuperar_cambio("pendiente", "2026-11-01T08:00:00", "")
    if estado in ("despachado", "recibido", "extraviado"):
        r.recuperar_cambio("despachado", "2026-11-01T10:00:00", "")
    if estado in ("recibido", "extraviado", "cancelado"):
        r.recuperar_cambio(estado, "2026-11-01T12:00:00", "")
    return r


def movimientos(remitos):
    b = crear_biblioteca()
    b.remitos.extend(remitos)
    return GeneradorReportes(Movimientos()).generar(b)


def test_movimientos_ejemplo_de_la_decision_del_grupo():
    remitos = [remito(n, "recibido", "bueno") for n in range(1, 8)]
    remitos += [remito(8, "recibido", "dañado"), remito(9, "extraviado"), remito(10, "cancelado")]
    fila = movimientos(remitos)[0]
    assert (fila["origen"], fila["destino"]) == ("Centro", "Norte")
    assert fila["envios"] == 10
    assert fila["recibidos_sin_novedad"] == 7
    assert fila["recibidos_con_danio"] == 1
    assert fila["extraviados"] == 1
    assert fila["cancelados"] == 1
    assert fila["tasa_envios_exitosos"] == 77.78
    # El tránsito promedio usa solo los recibidos: de despacho a recepción.
    assert fila["promedio_segundos_transito"] == 7200


def test_movimientos_en_curso_no_entran_en_la_tasa():
    fila = movimientos([remito(1, "recibido", "bueno"), remito(2, "pendiente"),
                        remito(3, "despachado"), remito(4, "cancelado")])[0]
    assert (fila["pendientes"], fila["en_transito"]) == (1, 1)
    assert fila["tasa_envios_exitosos"] == 100


def test_movimientos_sin_envios_finalizados_tasa_none():
    fila = movimientos([remito(1, "pendiente"), remito(2, "cancelado")])[0]
    assert fila["tasa_envios_exitosos"] is None
    assert fila["promedio_segundos_transito"] is None
