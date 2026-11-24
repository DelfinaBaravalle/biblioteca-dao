"""Vencimiento y multas (Vista 1): dias_atraso, multa y MULTA_DIARIA."""
from datetime import date, datetime, timedelta

from biblioteca.estados import id_estado
from biblioteca.modelos import Prestamo
from biblioteca.sistema import Biblioteca


def prestamo_con_vencimiento(vencimiento):
    return Prestamo(1, 1, 1, 1, 1, "2026-10-27", id_estado("Prestamo", "activo"),
                    "2026-10-27T10:00:00", vencimiento)


def test_multa_diaria_del_grupo():
    assert Biblioteca.MULTA_DIARIA == 500.0
    assert isinstance(Biblioteca.MULTA_DIARIA, float)
    assert Biblioteca.DIAS_PRESTAMO == 14


def test_dias_atraso_cuenta_solo_despues_del_vencimiento():
    p = prestamo_con_vencimiento("2026-11-10")
    assert p.dias_atraso(date(2026, 11, 1)) == 0
    assert p.dias_atraso(date(2026, 11, 10)) == 0
    assert p.dias_atraso(date(2026, 11, 11)) == 1
    assert p.dias_atraso(date(2026, 11, 13)) == 3
    assert p.dias_atraso(datetime(2026, 11, 13, 18, 30)) == 3


def test_sin_entrega_no_hay_atraso_ni_multa():
    p = Prestamo(1, 1, 1, 1, 2, "2026-11-01", id_estado("Prestamo", "esperando_envio"))
    assert p.dias_atraso(date(2030, 1, 1)) == 0
    assert p.multa(Biblioteca.MULTA_DIARIA, date(2030, 1, 1)) == 0


def test_multa_es_dias_por_tarifa():
    p = prestamo_con_vencimiento("2026-11-10")
    assert p.multa(500.0, date(2026, 11, 13)) == 1500.0
    assert p.multa(500.0, date(2026, 11, 9)) == 0
    assert p.multa(250.0, date(2026, 11, 13)) == 750.0


def test_multa_sin_fecha_se_calcula_a_hoy():
    p = prestamo_con_vencimiento((date.today() - timedelta(days=4)).isoformat())
    assert p.multa(Biblioteca.MULTA_DIARIA) == 2000.0
    assert p.vencido


def test_devolucion_tardia_conserva_su_multa():
    b = Biblioteca()
    b.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_libro("978-1", "Libro", "Autora")
    b.agregar_ejemplar("E1", 1, 1)
    p = b.prestar(1, 1, 1, 1)
    b.entregar(p.id)
    assert p.vencimiento == date.today() + timedelta(days=b.DIAS_PRESTAMO)
    p.vencimiento = date.today() - timedelta(days=5)  # Simula 5 días de atraso.
    b.devolver(p.id, "bueno")
    fecha_devolucion = b.devoluciones[0].fecha
    assert p.dias_atraso(fecha_devolucion) == 5
    # La fecha de corte es la devolución: el monto queda fijo aunque se consulte días después.
    assert p.multa(b.MULTA_DIARIA, fecha_devolucion) == 2500.0
    assert not p.vencido
