"""Pruebas unittest: todas las escrituras se realizan en directorios temporales."""
from datetime import date
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from biblioteca.web import crear_app
from biblioteca.orm import db, cargar_dominio, guardar_dominio
from sesion import iniciar_sesion


class PruebasWeb(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / 'prueba.db'
        self.config = {'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(self.ruta)}
        self.app = crear_app(self.config)
        self.addCleanup(self.cerrar)
        self.cliente = iniciar_sesion(self.app.test_client())
        for nombre in ('Centro', 'Norte', 'Sur'):
            self.post('/sedes', nombre=nombre, direccion='Calle 1', contacto='111', horarios='8 a 18')
        for dni, nombre in [('123', 'Ana'), ('456', 'Luis')]:
            self.post('/socios', dni=dni, nombre=nombre, contacto='correo')
        self.post('/libros', isbn='978-1', titulo='Libro uno', autor='Autora')
        self.post('/ejemplares', codigo='E1', libro_id=1, sede_id=1)

    def cerrar(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def post(self, url, esperado=201, **datos):
        respuesta = self.cliente.post('/api' + url, json=datos)
        self.assertEqual(respuesta.status_code, esperado, respuesta.json)
        return respuesta.json

    def get(self, coleccion):
        respuesta = self.cliente.get('/api/' + coleccion)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json

    def prestar(self, destino=1, socio=1):
        p = self.post('/prestamos', socio_id=socio, ejemplar_id=1, origen_id=1, destino_id=destino)
        if destino == 1:
            p = self.post(f"/prestamos/{p['id']}/entregar", esperado=200)
        return p

    def enviar(self, identificador):
        for accion in ('empaquetar', 'despachar', 'recibir'):
            extra = {'condicion': 'bueno'} if accion == 'recibir' else {}
            self.post(f'/remitos/{identificador}/avanzar', esperado=200,
                      accion=accion, observacion='Control de transporte', **extra)
        r = self.get('remitos')[identificador - 1]
        if r['tipo'] == 'ida':
            self.post(f"/prestamos/{r['prestamo_id']}/entregar", esperado=200)

    def test_frontend_y_recursos(self):
        self.assertEqual(self.cliente.get('/').status_code, 200)
        for recurso in ('app.js', 'estilos.css'):
            respuesta = self.cliente.get('/static/' + recurso)
            self.assertEqual(respuesta.status_code, 200)
            respuesta.close()

    def test_alta_edicion_y_estados(self):
        respuesta = self.cliente.patch('/api/sedes/1', json={'nombre': 'Central', 'horarios': '9 a 20'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.get('sedes')[0]['nombre'], 'Central')
        self.assertEqual(self.cliente.patch('/api/socios/1', json={'habilitado': False}).status_code, 200)
        self.prestar_rechazado()
        self.assertEqual(self.cliente.patch('/api/socios/1', json={'habilitado': True}).status_code, 200)
        self.assertEqual(self.cliente.patch('/api/libros/1', json={'titulo': 'Nuevo'}).status_code, 200)
        self.assertEqual(self.cliente.patch('/api/libros/1', json={'isbn': 'Otro'}).status_code, 400)

    def prestar_rechazado(self, destino=1, socio=1):
        self.post('/prestamos', esperado=400, socio_id=socio, ejemplar_id=1, origen_id=1, destino_id=destino)

    def test_local_devolucion_y_reparacion(self):
        p = self.prestar()
        self.assertEqual(p['estado'], 'activo')
        self.assertTrue(p['vencimiento'])
        self.prestar_rechazado(socio=2)
        self.assertEqual(len(self.get('solicitudes')), 1)  # El rechazo no deja solicitud huérfana.
        self.post('/devoluciones', prestamo_id=1, sede_id=1, condicion='dañado')
        self.assertEqual(self.get('ejemplares')[0]['estado'], 'fuera_servicio')
        self.post('/reparaciones', ejemplar_id=1, descripcion='Reparar cubierta')
        self.assertEqual(self.get('ejemplares')[0]['estado'], 'en_reparacion')
        self.post('/reparaciones', esperado=400, ejemplar_id=1, descripcion='Duplicada')
        self.post('/reparaciones/1/finalizar', esperado=400, resultado='dañado')
        self.post('/reparaciones/1/finalizar', esperado=200, resultado='bueno')
        self.assertEqual(self.get('ejemplares')[0]['estado'], 'disponible')
        self.assertEqual(self.get('reparaciones')[0]['resultado'], 'bueno')
        self.post('/reparaciones/1/finalizar', esperado=400, resultado='bueno')
        self.post('/devoluciones', esperado=400, prestamo_id=1, sede_id=1, condicion='bueno')

    def test_reparacion_irreparable(self):
        self.cliente.patch('/api/ejemplares/1', json={'condicion': 'dañado'})
        self.post('/reparaciones', ejemplar_id=1, descripcion='Evaluar material')
        self.post('/reparaciones/1/finalizar', esperado=200, resultado='inutilizable')
        self.assertEqual(self.get('ejemplares')[0]['estado'], 'fuera_servicio')
        # La reparación es para material dañado: un inutilizable ya no se repara.
        self.post('/reparaciones', esperado=400, ejemplar_id=1, descripcion='Segundo intento')
        self.assertEqual(len(self.get('reparaciones')), 1)

    def test_interbibliotecario_y_observer_persistente(self):
        p = self.prestar(2)
        self.assertIsNone(p['vencimiento'])
        self.post('/remitos/1/avanzar', esperado=400, accion='recibir', condicion='bueno')
        self.assertEqual(len(self.get('remitos')[0]['historial']), 1)
        self.post('/remitos/1/avanzar', esperado=200, accion='empaquetar')
        self.post('/remitos/1/avanzar', esperado=200, accion='despachar')
        self.assertIsNone(self.get('ejemplares')[0]['ubicacion_id'])
        self.post('/remitos/1/avanzar', esperado=200, accion='recibir', condicion='bueno')
        self.assertEqual(self.get('prestamos')[0]['estado'], 'listo_retiro')
        self.post('/prestamos/1/entregar', esperado=200)
        self.assertEqual(self.get('prestamos')[0]['estado'], 'activo')
        self.assertEqual(self.get('ejemplares')[0]['sede_id'], 1)
        self.post('/devoluciones', prestamo_id=1, sede_id=2, condicion='bueno')
        self.assertEqual(self.get('prestamos')[0]['estado'], 'retornando')
        self.prestar_rechazado()
        self.enviar(2)
        self.assertEqual(self.get('prestamos')[0]['estado'], 'devuelto')
        self.assertEqual(self.get('ejemplares')[0]['ubicacion_id'], 1)
        for r in self.get('remitos'):
            self.assertEqual([h['estado'] for h in r['historial']],
                             ['pendiente', 'empaquetado', 'despachado', 'recibido'])

    def test_devolucion_externa_desde_tercera_sede(self):
        self.prestar(2)
        self.enviar(1)
        self.post('/devoluciones', prestamo_id=1, sede_id=3, condicion='dañado')
        retorno = self.get('remitos')[1]
        self.assertEqual((retorno['origen_id'], retorno['destino_id']), (3, 1))
        self.assertEqual(self.get('devoluciones')[0]['sede_id'], 3)
        # La tercera sede también queda protegida mientras tiene un retorno.
        self.assertEqual(self.cliente.patch('/api/sedes/3', json={'activa': False}).status_code, 400)
        self.enviar(2)
        self.assertEqual(self.get('ejemplares')[0]['estado'], 'fuera_servicio')

    def test_local_devuelto_en_otra_sede_y_externo_devuelto_en_propietaria(self):
        self.prestar()
        self.post('/devoluciones', prestamo_id=1, sede_id=2, condicion='bueno')
        self.assertEqual(self.get('prestamos')[0]['estado'], 'retornando')
        self.enviar(1)
        self.prestar(2)
        self.enviar(2)
        self.post('/devoluciones', prestamo_id=2, sede_id=1, condicion='bueno')
        self.assertEqual(self.get('prestamos')[1]['estado'], 'devuelto')
        self.assertEqual(len(self.get('remitos')), 2)

    def test_solicitudes_asignacion_y_cancelacion(self):
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.post('/solicitudes', esperado=400, socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.post('/solicitudes/1/asignar', esperado=200)
        self.assertEqual(self.get('solicitudes')[0]['prestamo_id'], 1)
        self.post('/solicitudes/1/asignar', esperado=400)
        self.post('/solicitudes/1/cancelar', esperado=400)
        self.post('/solicitudes', socio_id=2, libro_id=1, origen_id=1, destino_id=1)
        self.post('/solicitudes/2/asignar', esperado=400)
        self.post('/solicitudes/2/cancelar', esperado=200)
        self.assertEqual(self.get('solicitudes')[1]['estado'], 'cancelada')

    def test_no_asignar_otro_libro_o_sede(self):
        self.post('/libros', isbn='9782', titulo='Otro', autor='Autor')
        self.post('/ejemplares', codigo='E2', libro_id=2, sede_id=1)
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.post('/solicitudes/1/asignar', esperado=400, ejemplar_id=2)
        self.post('/prestamos', esperado=400, socio_id=1, ejemplar_id=1, origen_id=2, destino_id=1)
        self.assertEqual(self.get('prestamos'), [])

    def test_reservas_fifo_y_cancelacion(self):
        for socio in (1, 2):
            self.post('/reservas', socio_id=socio, libro_id=1, sede_id=2)
        self.post('/reservas', esperado=400, socio_id=1, libro_id=1, sede_id=2)
        self.prestar_rechazado(2, 2)
        self.assertEqual(self.get('solicitudes'), [])
        self.post('/reservas/1/cancelar', esperado=200)
        self.prestar(2, 2)
        # La reserva sigue pendiente hasta la entrega al socio.
        self.assertEqual(self.get('reservas')[1]['estado'], 'pendiente')
        self.enviar(1)
        self.assertEqual(self.get('reservas')[1]['estado'], 'atendida')
        self.post('/reservas/2/cancelar', esperado=400)

    def test_sede_baja_solicitud_pendiente_y_socio_inhabilitado(self):
        self.cliente.patch('/api/sedes/2', json={'activa': False})
        self.prestar_rechazado(2)
        self.post('/reservas', esperado=400, socio_id=1, libro_id=1, sede_id=2)
        self.post('/solicitudes', esperado=400, socio_id=1, libro_id=1, origen_id=2, destino_id=1)
        self.post('/ejemplares', esperado=400, codigo='EN', libro_id=1, sede_id=2)
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=1)
        self.assertEqual(self.cliente.patch('/api/sedes/1', json={'activa': False}).status_code, 400)
        self.cliente.patch('/api/socios/1', json={'habilitado': False})
        self.post('/solicitudes/1/asignar', esperado=400)
        self.assertEqual(self.get('solicitudes')[0]['estado'], 'pendiente')

    def test_vencimientos_bloquean_hasta_devolucion(self):
        self.prestar()
        with self.app.app_context():
            sistema = cargar_dominio()
            sistema.prestamos[0].vencimiento = date(2000, 1, 1)
            guardar_dominio(sistema)
            db.session.commit()
        self.post('/reservas', esperado=400, socio_id=1, libro_id=1, sede_id=1)
        self.post('/solicitudes', esperado=400, socio_id=1, libro_id=1, origen_id=1, destino_id=1)
        self.assertTrue(self.get('prestamos')[0]['vencido'])
        self.post('/devoluciones', prestamo_id=1, sede_id=1, condicion='bueno')
        self.post('/reservas', socio_id=1, libro_id=1, sede_id=1)

    def test_duplicados_normalizados_y_payload_invalido(self):
        self.post('/socios', esperado=400, dni='00123', nombre='Otro', contacto='x')
        self.post('/libros', esperado=400, isbn='978 1', titulo='Otro', autor='x')
        # codigo se usa como nombre de campo de negocio: enviar directamente.
        r = self.cliente.post('/api/ejemplares', json={'codigo': 'e1', 'libro_id': 1, 'sede_id': 1})
        self.assertEqual(r.status_code, 400)
        casos = [None, [], {'nombre': 'X'}, {'nombre': 12, 'direccion': 'x', 'contacto': 'x', 'horarios': 'x'},
                 {'nombre': 'X', 'direccion': 'x', 'contacto': 'x', 'horarios': 'x', 'extra': 'x'}]
        for datos in casos:
            self.assertEqual(self.cliente.post('/api/sedes', json=datos).status_code, 400)
        for valor in ('1', True, -1, 0, None, 1.5):
            r = self.cliente.post('/api/reservas', json={'socio_id': valor, 'libro_id': 1, 'sede_id': 1})
            self.assertEqual(r.status_code, 400)
        self.assertEqual(self.cliente.patch('/api/socios/1', json={'habilitado': 'false'}).status_code, 400)

    def test_error_devolucion_y_edicion_atomicas(self):
        self.prestar()
        antes = self.get('estado')
        self.post('/devoluciones', esperado=400, prestamo_id=1, sede_id=1, condicion='rota')
        self.assertEqual(self.get('estado'), antes)
        respuesta = self.cliente.patch('/api/sedes/3', json={'activa': False, 'direccion': ''})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(self.get('estado'), antes)

    def test_rollback_error_sql_despues_de_escribir(self):
        antes = self.get('estado')
        original = guardar_dominio

        def fallar(sistema):
            original(sistema)
            raise IntegrityError('INSERT', {}, Exception('Error inducido'))

        with patch('biblioteca.web.guardar_dominio', side_effect=fallar):
            self.post('/prestamos', esperado=409, socio_id=1, ejemplar_id=1, origen_id=1, destino_id=2)
        self.assertEqual(self.get('estado'), antes)
        self.prestar(2)

    def test_persistencia_entre_instancias(self):
        self.prestar(2)
        self.post('/remitos/1/avanzar', esperado=200, accion='empaquetar')
        antes = self.get('estado')
        otra = crear_app(self.config)
        with otra.app_context():
            self.assertEqual(iniciar_sesion(otra.test_client()).get('/api/estado').json, antes)
            db.session.remove()
            db.engine.dispose()
        self.post('/remitos/1/avanzar', esperado=200, accion='despachar')
        self.assertEqual(len(self.get('remitos')[0]['historial']), 3)

    def test_dos_asignaciones_concurrentes_no_duplican_prestamo(self):
        barrera = threading.Barrier(2)
        respuestas = []

        def prestar(socio):
            with self.app.test_client() as cliente:
                iniciar_sesion(cliente)
                barrera.wait()
                r = cliente.post('/api/prestamos', json={'socio_id': socio, 'ejemplar_id': 1,
                                                        'origen_id': 1, 'destino_id': 2})
                respuestas.append(r.status_code)
        hilos = [threading.Thread(target=prestar, args=(s,)) for s in (1, 2)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=10)
            self.assertFalse(h.is_alive())
        self.assertEqual(sorted(respuestas), [201, 400])
        self.assertEqual(len(self.get('prestamos')), 1)
        self.assertEqual(len(self.get('remitos')), 1)
        self.assertEqual(len(self.get('solicitudes')), 1)

    def test_disponibilidad_y_cuatro_reportes(self):
        self.assertEqual(len(self.get('disponibilidad?libro_id=1&sede_id=1')), 1)
        self.prestar(2)
        self.enviar(1)
        ranking = self.get('reportes/solicitados')
        self.assertEqual(ranking[0]['porcentaje'], 100)
        movimientos = self.get('reportes/movimientos')
        self.assertEqual(movimientos[0]['tasa_envios_exitosos'], 100)
        self.assertIsNotNone(movimientos[0]['promedio_segundos_transito'])
        self.assertEqual(len(self.get('reportes/prestamos')['detalle']), 1)
        self.assertEqual(len(self.get('reportes/disponibilidad')['detalle']), 2)
        self.assertEqual(self.get('reportes/solicitados?desde=1900-01-01&hasta=1900-12-31'), [])
        self.assertEqual(self.cliente.get('/api/reportes/movimientos?desde=2026-12-01&hasta=2026-01-01').status_code, 400)
        self.assertEqual(self.cliente.get('/api/reportes/prestamos?desde=mal').status_code, 400)
        self.assertEqual(self.cliente.get('/api/disponibilidad').status_code, 400)

    def test_cuatro_reportes_en_pdf(self):
        self.prestar(2)
        self.enviar(1)
        for tipo in ('prestamos', 'disponibilidad', 'solicitados', 'movimientos'):
            respuesta = self.cliente.get(f'/api/reportes/{tipo}/pdf?desde=2026-01-01&hasta=2099-12-31')
            self.assertEqual(respuesta.status_code, 200, tipo)
            self.assertEqual(respuesta.mimetype, 'application/pdf')
            self.assertTrue(respuesta.data.startswith(b'%PDF'), tipo)
            self.assertIn(f'reporte-{tipo}-', respuesta.headers['Content-Disposition'])
        # Sin datos en el período también se genera, con la tabla vacía avisada.
        vacio = self.cliente.get('/api/reportes/solicitados/pdf?desde=1900-01-01&hasta=1900-12-31')
        self.assertEqual(vacio.status_code, 200)
        self.assertEqual(self.cliente.get('/api/reportes/inexistente/pdf').status_code, 404)
        self.assertEqual(self.cliente.get('/api/reportes/movimientos/pdf?desde=2026-12-01&hasta=2026-01-01').status_code, 400)
        self.assertEqual(self.cliente.get('/api/reportes/prestamos/pdf?desde=mal').status_code, 400)

    def test_solicitud_sin_copia_guarda_la_reserva(self):
        # Decisión 24: la solicitud y la reserva automática se guardan en la misma transacción.
        self.prestar(1, socio=2)
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        reservas = self.get('reservas')
        self.assertEqual([(r['socio_id'], r['libro_id'], r['sede_id'], r['estado']) for r in reservas],
                         [(1, 1, 2, 'pendiente')])
        self.post('/solicitudes/2/cancelar', esperado=200)
        self.assertEqual(self.get('reservas')[0]['estado'], 'cancelada')

    def test_reserva_informa_su_prestamo_en_curso(self):
        # Decisión 26: el dato se calcula al consultar; en la base la reserva sigue pendiente.
        self.prestar(1, socio=2)  # Luis compromete la única copia
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        reserva = self.get('reservas')[0]
        self.assertEqual((reserva['estado'], reserva['prestamo_en_curso']), ('pendiente', None))
        self.post('/devoluciones', prestamo_id=1, sede_id=1, condicion='bueno')  # se libera la copia
        self.post('/solicitudes/2/asignar', esperado=200)
        prestamo = self.get('prestamos')[-1]
        reserva = self.get('reservas')[0]
        self.assertEqual((reserva['estado'], reserva['prestamo_en_curso']), ('pendiente', prestamo['id']))
        # Si el envío se cancela, deja de estar en curso y conserva su lugar.
        self.post('/remitos/1/avanzar', esperado=200, accion='cancelar')
        reserva = self.get('reservas')[0]
        self.assertEqual((reserva['estado'], reserva['prestamo_en_curso']), ('pendiente', None))
        # Con una nueva solicitud que llega bien, al entregar queda atendida.
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.post('/solicitudes/3/asignar', esperado=200)
        self.enviar(2)
        reserva = self.get('reservas')[0]
        self.assertEqual((reserva['estado'], reserva['prestamo_en_curso']), ('atendida', None))
        self.assertEqual(len(self.get('reservas')), 1)

    def test_ranking_cuenta_prestamos_interbibliotecarios_no_cancelados(self):
        # Una solicitud pendiente todavía no es un préstamo: no entra en el ranking.
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.assertEqual(self.get('reportes/solicitados'), [])
        self.post('/solicitudes/1/asignar', esperado=200)
        self.assertEqual(self.get('reportes/solicitados')[0]['prestamos'], 1)
        # El envío se cancela y se vuelve a pedir: cuenta una sola vez.
        self.post('/remitos/1/avanzar', esperado=200, accion='cancelar')
        self.assertEqual(self.get('reportes/solicitados'), [])
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.post('/solicitudes/2/asignar', esperado=200)
        fila = self.get('reportes/solicitados')[0]
        self.assertEqual((fila['prestamos'], fila['porcentaje']), (1, 100))

    def test_movimientos_pendientes_no_tienen_promedio(self):
        self.prestar(2)
        fila = self.get('reportes/movimientos')[0]
        self.assertEqual(fila['pendientes'], 1)
        self.assertIsNone(fila['tasa_envios_exitosos'])
        self.assertIsNone(fila['promedio_segundos_transito'])

    def test_rutas_invalidas(self):
        self.assertEqual(self.cliente.get('/api/noexiste').status_code, 404)
        self.assertEqual(self.cliente.get('/api/sedes/999').status_code, 404)
        self.post('/remitos', esperado=405)
        self.assertEqual(self.cliente.delete('/api/sedes/1').status_code, 405)


if __name__ == '__main__':
    unittest.main()
