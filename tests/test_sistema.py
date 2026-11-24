from datetime import date, timedelta

import pytest

from biblioteca.sistema import Biblioteca
from biblioteca.modelos import Remito
from biblioteca.reportes import (GeneradorReportes, PrestamosActivos, Disponibilidad,
                                MasSolicitados, Movimientos)
from biblioteca.observadores import ObservadorRemito


def crear_biblioteca():
    b = Biblioteca()
    b.agregar_sede('Centro', 'Calle 1', '111', '8 a 18')
    b.agregar_sede('Norte', 'Calle 2', '222', '8 a 18')
    b.agregar_socio('123', 'Ana', 'ana@mail')
    b.agregar_socio('456', 'Luis', 'luis@mail')
    b.agregar_libro('978-1', 'El principito', 'Saint-Exupéry')
    b.agregar_ejemplar('E1', 1, 1)
    return b

def enviar(b, remito_id):
    b.avanzar_remito(remito_id, 'empaquetar', 'Control realizado')
    b.avanzar_remito(remito_id, 'despachar', 'Control realizado')
    b.avanzar_remito(remito_id, 'recibir', 'Control realizado', 'bueno')
    remito = b.buscar('remitos', remito_id)
    if remito.tipo == 'ida':
        b.entregar(remito.prestamo_id)

def test_prestamo_local_y_danio():
    b = crear_biblioteca()
    p = b.prestar(1, 1, 1, 1)
    b.entregar(p.id)
    assert p.vencimiento == date.today() + timedelta(days=14)
    with pytest.raises(ValueError):
        b.prestar(2, 1, 1, 1)
    b.devolver(p.id, 'dañado')
    assert b.ejemplares[0].estado.es('fuera_servicio')
    assert b.disponibles(1, 1) == []
    reparacion = b.iniciar_reparacion(1, 'Reparación de cubierta')
    b.finalizar_reparacion(reparacion.id, 'bueno')
    assert len(b.disponibles(1, 1)) == 1
    with pytest.raises(ValueError):
        b.devolver(p.id, 'bueno')

def test_circuito_interbibliotecario_completo():
    b = crear_biblioteca()
    p = b.prestar(1, 1, 1, 2)
    assert p.vencimiento is None
    with pytest.raises(ValueError):
        b.avanzar_remito(1, 'recibir', condicion='bueno')
    assert len(b.remitos[0].consultar_historial()) == 1
    b.avanzar_remito(1, 'empaquetar')
    b.avanzar_remito(1, 'despachar')
    assert b.ejemplares[0].ubicacion_id is None
    b.avanzar_remito(1, 'recibir', condicion='bueno')
    assert p.estado.es('listo_retiro')
    b.entregar(p.id)
    assert p.estado.es('activo')
    assert b.ejemplares[0].sede_id == 1
    assert b.ejemplares[0].ubicacion_id == 2
    b.devolver(1, 'bueno')
    assert p.estado.es('retornando')
    assert b.remitos[1].origen_id == 2
    enviar(b, 2)
    assert p.estado.es('devuelto')
    assert len(b.disponibles(1, 1)) == 1
    for r in b.remitos:
        assert [h['estado'] for h in r.consultar_historial()] == ['pendiente', 'empaquetado', 'despachado', 'recibido']
        with pytest.raises(ValueError):
            b.avanzar_remito(r.id, 'recibir', condicion='bueno')

def test_socio_inhabilitado_y_vencido():
    b = crear_biblioteca()
    b.cambiar_socio(1, False)
    with pytest.raises(ValueError):
        b.prestar(1, 1, 1, 1)
    b.cambiar_socio(1, True)
    p = b.prestar(1, 1, 1, 1)
    b.entregar(p.id)
    p.vencimiento = date.today() - timedelta(days=3)
    with pytest.raises(ValueError):
        b.reservar(1, 1, 1)
    reporte = GeneradorReportes(PrestamosActivos()).generar(b)
    assert reporte['detalle'][0]['dias_atraso'] == 3
    assert reporte['totales_por_sede']['Centro']['vencidos'] == 1
    b.devolver(1, 'bueno')

def test_sedes_y_pertenencia():
    b = crear_biblioteca()
    with pytest.raises(ValueError):
        b.prestar(1, 1, 2, 1)
    b.cambiar_sede(2, False)
    with pytest.raises(ValueError):
        b.prestar(1, 1, 1, 2)
    with pytest.raises(ValueError):
        b.reservar(1, 1, 2)
    b.cambiar_sede(2, True)
    b.prestar(1, 1, 1, 2)
    for sede_id in (1, 2):
        with pytest.raises(ValueError):
            b.cambiar_sede(sede_id, False)

def test_duplicados():
    b = crear_biblioteca()
    acciones = [lambda: b.agregar_socio('00123', 'Otro', 'mail'), lambda: b.agregar_libro('9781', 'Otro', 'Autor'), lambda: b.agregar_ejemplar('e1', 1, 1)]
    for accion in acciones:
        with pytest.raises(ValueError):
            accion()

def test_reservas_orden_cancelacion_y_atencion():
    b = crear_biblioteca()
    r1 = b.reservar(1, 1, 2)
    r2 = b.reservar(2, 1, 2)
    with pytest.raises(ValueError):
        b.reservar(1, 1, 2)
    with pytest.raises(ValueError):
        b.prestar(2, 1, 1, 2)
    assert len(b.prestamos) == 0
    b.cancelar_reserva(r1.id)
    b.prestar(2, 1, 1, 2)
    # La reserva se atiende al entregar el libro, no al asignar el préstamo.
    assert r2.estado.es('pendiente')
    enviar(b, 1)
    assert r2.estado.es('atendida')

def test_persistencia_con_historial(recargar):
    b = crear_biblioteca()
    b.prestar(1, 1, 1, 2)
    enviar(b, 1)
    copia = recargar(b)
    assert [r.a_fila() for r in copia.remitos] == [r.a_fila() for r in b.remitos]
    assert copia.remitos[0].consultar_historial() == b.remitos[0].consultar_historial()
    assert [p.a_fila() for p in copia.prestamos] == [p.a_fila() for p in b.prestamos]
    copia.devolver(1, 'bueno')
    assert copia.remitos[-1].id == 2

def test_reportes_calculos_y_filtros():
    b = crear_biblioteca()
    b.prestar(1, 1, 1, 2)
    enviar(b, 1)
    r = Remito(1, 1, 1, 1, 2, 'ida', 'recibido', 'bueno')
    r.recuperar_cambio('pendiente', '2026-01-01T08:00:00', '')
    r.recuperar_cambio('empaquetado', '2026-01-01T09:00:00', '')
    r.recuperar_cambio('despachado', '2026-01-01T10:00:00', '')
    r.recuperar_cambio('recibido', '2026-01-02T10:00:00', '')
    b.remitos[0] = r
    movimientos = GeneradorReportes(Movimientos()).generar(b)
    assert movimientos[0]['promedio_segundos_transito'] == 24 * 3600
    assert movimientos[0]['tasa_envios_exitosos'] == 100
    ranking = GeneradorReportes(MasSolicitados()).generar(b)
    assert ranking[0]['prestamos'] == 1
    assert ranking[0]['porcentaje'] == 100
    disponibles = GeneradorReportes(Disponibilidad()).generar(b)['detalle']
    assert disponibles[0]['propios_prestados'] == 1
    assert disponibles[1]['presentes'] == 1
    assert GeneradorReportes(MasSolicitados()).generar(b, '2000-01-01', '2000-12-31') == []
    with pytest.raises(ValueError):
        GeneradorReportes(Movimientos()).generar(b, '2026-02-01', '2026-01-01')

def test_reportes_sin_datos():
    vacio = Biblioteca()
    for reporte in (PrestamosActivos(), Disponibilidad(), MasSolicitados(), Movimientos()):
        assert GeneradorReportes(reporte).generar(vacio) is not None


def test_creacion_directa_de_los_cuatro_reportes():
    for tipo in (PrestamosActivos, Disponibilidad, MasSolicitados, Movimientos):
        reporte = tipo()
        assert isinstance(reporte, tipo)
        assert GeneradorReportes(reporte).generar(Biblioteca()) is not None


class ObservadorPrueba(ObservadorRemito):
    def __init__(self):
        self.cambios = []

    def actualizar(self, remito, observacion):
        self.cambios.append((remito.estado, observacion))


def test_observer_notifica_solo_transiciones_validas():
    b = crear_biblioteca()
    b.prestar(1, 1, 1, 2)
    remito = b.remitos[0]
    observador = ObservadorPrueba()
    remito.suscribir(observador)
    remito.suscribir(observador)
    with pytest.raises(ValueError):
        b.avanzar_remito(1, 'recibir', condicion='bueno')
    assert observador.cambios == []
    assert len(remito.consultar_historial()) == 1
    b.avanzar_remito(1, 'empaquetar', '  Embalaje controlado  ')
    assert observador.cambios == [('empaquetado', 'Embalaje controlado')]
    assert len(remito.consultar_historial()) == 2
    remito.desuscribir(observador)
    b.avanzar_remito(1, 'despachar')
    assert len(observador.cambios) == 1
    assert len(remito.consultar_historial()) == 3


def test_propiedades_y_proteccion_del_historial():
    b = crear_biblioteca()
    ejemplar = b.ejemplares[0]
    with pytest.raises(ValueError):
        ejemplar.condicion = 'desconocida'
    assert ejemplar.condicion == 'bueno'
    with pytest.raises(AttributeError):
        b.socios[0].dni = '999'
    b.prestar(1, 1, 1, 2)
    remito = b.remitos[0]
    with pytest.raises(AttributeError):
        remito.estado = 'recibido'
    historial = remito.consultar_historial()
    historial[0]['estado'] = 'recibido'
    historial.clear()
    assert remito.consultar_historial()[0]['estado'] == 'pendiente'


def test_recuperacion_reconecta_el_observador(recargar):
    b = crear_biblioteca()
    b.prestar(1, 1, 1, 2)
    b.avanzar_remito(1, 'empaquetar')
    copia = recargar(b)
    assert len(copia.remitos[0].consultar_historial()) == 2
    copia.avanzar_remito(1, 'despachar')
    copia.avanzar_remito(1, 'recibir', condicion='bueno')
    copia.entregar(1)
    segunda_copia = recargar(copia)
    assert segunda_copia.prestamos[0].estado.es('activo')
    assert [c['estado'] for c in segunda_copia.remitos[0].consultar_historial()] == [
        'pendiente', 'empaquetado', 'despachado', 'recibido']


def test_edicion_y_devolucion_invalida_no_alteran_datos():
    b = crear_biblioteca()
    with pytest.raises(ValueError):
        b.editar('sedes', 1, nombre='Nuevo nombre', direccion='')
    assert b.sedes[0].nombre == 'Centro'
    prestamo = b.prestar(1, 1, 1, 1)
    b.entregar(prestamo.id)
    with pytest.raises(ValueError):
        b.devolver(prestamo.id, 'desconocida')
    assert prestamo.estado.es('activo')
    assert b.devoluciones == []
    assert b.ejemplares[0].estado.es('prestado')


# Decisión 24: una solicitud que no se puede asignar ahora suma al socio a la fila de reservas.

def test_solicitud_sin_copia_crea_la_reserva():
    b = crear_biblioteca()
    b.prestar(2, 1, 1, 1)  # Luis compromete la única copia
    s = b.solicitar(1, 1, 1, 2)
    assert s.estado.es('pendiente')
    assert len(b.reservas) == 1
    reserva = b.reservas[0]
    assert (reserva.socio_id, reserva.libro_id, reserva.sede_id) == (1, 1, 2)
    assert reserva.estado.es('pendiente')


def test_solicitud_con_copia_y_sin_fila_no_crea_reserva():
    b = crear_biblioteca()
    b.solicitar(1, 1, 1, 2)
    assert b.reservas == []


def test_solicitud_con_fila_de_otro_socio_queda_detras():
    b = crear_biblioteca()
    b.reservar(2, 1, 2)  # Luis espera el libro en Norte
    b.solicitar(1, 1, 1, 2)  # hay copia, pero Luis está primero
    assert [(r.socio_id, r.estado.nombre) for r in b.reservas] == [(2, 'pendiente'), (1, 'pendiente')]
    with pytest.raises(ValueError, match='prioridad'):
        b.asignar_solicitud(1)


def test_solicitud_reusa_la_reserva_que_ya_tenia():
    b = crear_biblioteca()
    b.prestar(2, 1, 1, 1)
    previa = b.reservar(1, 1, 2)
    b.solicitar(1, 1, 1, 2)
    assert b.reservas == [previa]


def test_cancelar_la_solicitud_cancela_su_reserva():
    b = crear_biblioteca()
    b.prestar(2, 1, 1, 1)
    s = b.solicitar(1, 1, 1, 2)
    b.cancelar_solicitud(s.id)
    assert b.reservas[0].estado.es('cancelada')


def test_reserva_automatica_se_atiende_al_entregar():
    b = crear_biblioteca()
    prestamo_luis = b.prestar(2, 1, 1, 1)
    b.entregar(prestamo_luis.id)
    s = b.solicitar(1, 1, 1, 2)  # sin copia: Ana queda en la fila
    b.devolver(prestamo_luis.id, 'bueno', 1)
    b.asignar_solicitud(s.id)
    assert b.reservas[0].estado.es('pendiente')  # recién se atiende al entregar
    enviar(b, b.remitos[-1].id)
    assert b.reservas[0].estado.es('atendida')
