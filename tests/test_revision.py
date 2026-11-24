"""Segunda revisión: reglas de entrega, inventario, validaciones y persistencia aislada."""
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch, Mock

from sqlalchemy.exc import IntegrityError

import test_web as base_web
from sesion import iniciar_sesion
from biblioteca.orm import (db, cargar_dominio, guardar_dominio, EntregaFila,
                            PrestamoFila, HistorialFila)
from biblioteca.observadores import ObservadorRemito
from biblioteca.modelos import Remito
from biblioteca.web import REPORTES


class RevisionIntegral(unittest.TestCase):
    setUp = base_web.PruebasWeb.setUp
    cerrar = base_web.PruebasWeb.cerrar
    post = base_web.PruebasWeb.post
    get = base_web.PruebasWeb.get
    enviar = base_web.PruebasWeb.enviar
    prestar = base_web.PruebasWeb.prestar

    def test_externo_exige_entrega_despues_de_recepcion(self):
        self.prestar(2)
        for accion in (None, 'empaquetar', 'despachar', 'recibir'):
            if accion:
                extra = {'condicion': 'bueno'} if accion == 'recibir' else {}
                self.post('/remitos/1/avanzar', esperado=200, accion=accion, **extra)
            antes = self.get('estado')
            self.post('/devoluciones', esperado=400, prestamo_id=1, sede_id=2, condicion='bueno')
            if accion != 'recibir':
                self.post('/prestamos/1/entregar', esperado=400)
            self.assertEqual(self.get('estado'), antes)
        p = self.get('prestamos')[0]
        self.assertEqual(p['estado'], 'listo_retiro')
        self.assertIsNone(p['inicio'])
        self.assertIsNone(p['vencimiento'])
        self.assertEqual(self.get('ejemplares')[0]['estado'], 'comprometido')
        p = self.post('/prestamos/1/entregar', esperado=200)
        self.assertEqual(p['estado'], 'activo')
        self.assertEqual(p['vencimiento'], (date.today()+timedelta(days=14)).isoformat())
        self.post('/prestamos/1/entregar', esperado=400)
        self.post('/devoluciones', prestamo_id=1, sede_id=2, condicion='bueno')
        self.assertLessEqual(p['inicio'], self.get('devoluciones')[0]['fecha'])
        self.assertEqual(len(self.get('entregas')), 1)

    def test_local_tambien_requiere_entrega_explicita(self):
        p = self.post('/prestamos', socio_id=1, ejemplar_id=1, origen_id=1, destino_id=1)
        self.assertEqual(p['estado'], 'listo_retiro')
        self.post('/devoluciones', esperado=400, prestamo_id=1, sede_id=1, condicion='bueno')
        self.post('/prestamos/1/entregar', esperado=200)
        self.post('/devoluciones', prestamo_id=1, sede_id=1, condicion='bueno')
        self.post('/devoluciones', esperado=400, prestamo_id=1, sede_id=1, condicion='bueno')

    def test_inhabilitado_no_recibe_material_pero_puede_devolver(self):
        self.post('/prestamos', socio_id=1, ejemplar_id=1, origen_id=1, destino_id=1)
        self.cliente.patch('/api/socios/1', json={'habilitado': False})
        self.post('/prestamos/1/entregar', esperado=400)
        self.cliente.patch('/api/socios/1', json={'habilitado': True})
        self.post('/prestamos/1/entregar', esperado=200)
        self.cliente.patch('/api/socios/1', json={'habilitado': False})
        self.post('/devoluciones', prestamo_id=1, sede_id=1, condicion='bueno')

    def test_fifo_no_salta_socio_inhabilitado(self):
        for socio in (1, 2):
            self.post('/reservas', socio_id=socio, libro_id=1, sede_id=2)
        self.cliente.patch('/api/socios/1', json={'habilitado': False})
        self.post('/prestamos', esperado=400, socio_id=2, ejemplar_id=1, origen_id=1, destino_id=2)
        self.post('/reservas/1/cancelar', esperado=200)
        self.post('/prestamos', socio_id=2, ejemplar_id=1, origen_id=1, destino_id=2)
        self.assertEqual(self.get('reservas')[1]['estado'], 'pendiente')

    def test_horarios_estructurados_y_texto_libre(self):
        sede = self.post('/sedes', nombre='Oeste', direccion='4', contacto='444',
                         dias='Lunes a viernes', apertura='08:30', cierre='18:45')
        self.assertEqual(sede['horarios'], 'Lunes a viernes | 08:30 a 18:45')
        for apertura, cierre in [('18:00','08:00'), ('25:00','26:00'), ('08:60','18:00'), ('8:00','18:00'), ('08:00','08:00')]:
            self.post('/sedes', esperado=400, nombre='Invalida', direccion='x', contacto='x',
                      dias='Lunes', apertura=apertura, cierre=cierre)
        self.post('/sedes', esperado=400, nombre='Sin días', direccion='x', contacto='x', apertura='08:00', cierre='18:00')
        # El documento define horarios como texto: uno escrito a mano se acepta si no está vacío.
        self.post('/sedes', nombre='Turnos', direccion='x', contacto='x', horarios='Atención por turnos')
        self.post('/sedes', esperado=400, nombre='Vacía', direccion='x', contacto='x', horarios='  ')
        self.assertEqual(self.cliente.patch('/api/sedes/1', json={'horarios':'Atención por turnos especiales'}).status_code, 200)
        self.assertEqual(self.get('sedes')[0]['horarios'], 'Atención por turnos especiales')

    def test_validacion_socios_y_codigo_catalogo_interno(self):
        for dni in ('0','000','12a','１２３','12345678901','-1'):
            self.post('/socios', esperado=400, dni=dni, nombre='Nueva', contacto='123')
        for nombre in ('  ', '123', '...'):
            self.post('/socios', esperado=400, dni='789', nombre=nombre, contacto='123')
        for contacto in ('  ','@@correo','sin espacio@','---','x\ny'):
            self.post('/socios', esperado=400, dni='789', nombre='Nueva', contacto=contacto)
        self.post('/libros', isbn='PRUEBA001', titulo='Código interno', autor='Autor')
        self.post('/libros', esperado=400, isbn='prueba-001', titulo='Duplicado', autor='Autor')
        self.assertEqual(self.get('libros')[1]['isbn'], 'PRUEBA001')

    def test_baja_reactivacion_solicitud_y_prestamo_listo(self):
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        for sede in (1,2):
            self.assertEqual(self.cliente.patch(f'/api/sedes/{sede}',json={'activa':False}).status_code,400)
        self.post('/solicitudes/1/cancelar', esperado=200)
        self.assertEqual(self.cliente.patch('/api/sedes/2',json={'activa':False}).status_code,200)
        self.post('/solicitudes', esperado=400, socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.assertEqual(self.cliente.patch('/api/sedes/2',json={'activa':True}).status_code,200)
        self.post('/prestamos', socio_id=1, ejemplar_id=1, origen_id=1, destino_id=1)
        self.assertEqual(self.cliente.patch('/api/sedes/1',json={'activa':False}).status_code,400)

    def test_solicitudes_incompatibles_no_asignan_otra_copia(self):
        self.post('/ejemplares', codigo='E2', libro_id=1, sede_id=1)
        self.post('/solicitudes', socio_id=1, libro_id=1, origen_id=1, destino_id=2)
        self.post('/solicitudes', esperado=400, socio_id=1, libro_id=1, origen_id=1, destino_id=3)
        self.post('/solicitudes/1/asignar', esperado=200)
        self.post('/prestamos', esperado=400, socio_id=1, ejemplar_id=2, origen_id=1, destino_id=2)
        self.assertEqual(len(self.get('prestamos')), 1)
        self.assertEqual(self.get('ejemplares')[1]['estado'],'disponible')

    def test_inventario_muestra_comprometidos_transito_y_sede_baja(self):
        self.prestar(2)
        self.assertEqual(self.get('disponibilidad?libro_id=1&sede_id=1'), [])
        fila = self.get('disponibilidad?libro_id=1&sede_id=1&modo=todos')[0]
        self.assertFalse(fila['disponible'])
        self.assertIn('comprometido', fila['motivo'])
        self.post('/remitos/1/avanzar', esperado=200, accion='empaquetar')
        self.post('/remitos/1/avanzar', esperado=200, accion='despachar')
        fila = self.get('disponibilidad?libro_id=1&sede_id=1&modo=todos')[0]
        self.assertIsNone(fila['ubicacion_id'])
        self.assertIn('tránsito', fila['motivo'])
        self.post('/remitos/1/avanzar', esperado=200, accion='recibir', condicion='bueno')
        fila = self.get('disponibilidad?libro_id=1&sede_id=2&modo=todos')[0]
        self.assertEqual((fila['sede_id'],fila['ubicacion_id']), (1,2))
        self.assertIn('otra sede',fila['motivo'])
        self.assertEqual(self.get('disponibilidad?libro_id=1&sede_id=3&modo=todos'), [])
        self.cliente.patch('/api/sedes/3',json={'activa':False})
        self.assertEqual(self.get('disponibilidad?libro_id=1&sede_id=3&modo=todos'), [])

    def test_reparacion_no_se_salta_desde_administracion(self):
        self.prestar()
        self.post('/devoluciones',prestamo_id=1,sede_id=1,condicion='dañado')
        self.assertEqual(self.cliente.patch('/api/ejemplares/1',json={'condicion':'bueno'}).status_code,400)
        self.assertEqual(self.get('ejemplares')[0]['condicion'],'dañado')
        self.post('/reparaciones',ejemplar_id=1,descripcion='Restaurar')
        self.assertEqual(self.cliente.patch('/api/ejemplares/1',json={'condicion':'bueno'}).status_code,400)
        self.post('/reparaciones/1/finalizar',esperado=200,resultado='bueno')
        self.assertEqual(self.get('ejemplares')[0]['estado'],'disponible')
        self.post('/reparaciones',esperado=400,ejemplar_id=1,descripcion='Sin daño')

    def test_danio_pendiente_retorno_no_se_repara_ni_asigna(self):
        self.prestar(2)
        self.enviar(1)
        self.post('/devoluciones',prestamo_id=1,sede_id=3,condicion='dañado')
        self.post('/reparaciones',esperado=400,ejemplar_id=1,descripcion='Todavía en retorno')
        self.post('/prestamos',esperado=400,socio_id=2,ejemplar_id=1,origen_id=1,destino_id=1)
        self.enviar(2)
        self.assertEqual(self.get('ejemplares')[0]['condicion'],'dañado')
        self.assertEqual(self.get('prestamos')[0]['condicion_devolucion'],'dañado')
        self.post('/reparaciones',ejemplar_id=1,descripcion='Ahora sí')

    def test_rollback_conjunto_de_estado_e_historial_observer(self):
        self.prestar(2)
        antes=self.get('estado')
        original=guardar_dominio
        def fallar(sistema):
            original(sistema)
            raise IntegrityError('INSERT',{},Exception('Fallo inducido'))
        with patch('biblioteca.web.guardar_dominio',side_effect=fallar):
            self.post('/remitos/1/avanzar',esperado=409,accion='empaquetar')
        self.assertEqual(self.get('estado'),antes)
        self.post('/remitos/1/avanzar',esperado=200,accion='empaquetar')
        self.assertEqual(len(self.get('remitos')[0]['historial']),2)

    def test_observer_recuperado_notifica_una_sola_vez(self):
        self.prestar(2)
        class Observador(ObservadorRemito):
            def __init__(self): self.eventos=[]
            def actualizar(self,remito,observacion): self.eventos.append((remito.estado,observacion))
        with self.app.app_context():
            sistema=cargar_dominio()
            remito=sistema.remitos[0]
            observado=Observador()
            remito.suscribir(observado)
            remito.suscribir(observado)
            self.assertEqual(len(remito.consultar_historial()),1)
            with self.assertRaises(ValueError):sistema.avanzar_remito(1,'recibir',condicion='bueno')
            self.assertEqual(observado.eventos,[])
            sistema.avanzar_remito(1,'empaquetar','Prueba')
            self.assertEqual(observado.eventos,[('empaquetado','Prueba')])
            guardar_dominio(sistema)
            db.session.commit()
        self.assertEqual(len(self.get('remitos')[0]['historial']),2)

    def test_entrega_rollback_y_relacion_orm_persistente(self):
        self.post('/prestamos',socio_id=1,ejemplar_id=1,origen_id=1,destino_id=1)
        antes=self.get('estado')
        with patch('biblioteca.web.guardar_dominio',side_effect=IntegrityError('INSERT',{},Exception())):
            self.post('/prestamos/1/entregar',esperado=409)
        self.assertEqual(self.get('estado'),antes)
        self.post('/prestamos/1/entregar',esperado=200)
        with self.app.app_context():
            entrega=db.session.get(EntregaFila,1)
            self.assertEqual(entrega.prestamo.id,1)
            self.assertEqual(db.session.get(PrestamoFila,1).registro_entrega.id,entrega.id)
            db.session.add(EntregaFila(prestamo_id=999,fecha='2026-01-01'))
            with self.assertRaises(IntegrityError):db.session.commit()
            db.session.rollback()
        self.assertEqual(len(self.get('entregas')),1)

    def test_historial_de_prestamos_sucesivos_no_se_pierde(self):
        for numero in (1,2):
            self.prestar()
            self.post('/devoluciones',prestamo_id=numero,sede_id=1,condicion='bueno')
        self.assertEqual([p['id'] for p in self.get('prestamos')],[1,2])
        self.assertEqual(len(self.get('entregas')),2)
        self.assertEqual(len(self.get('devoluciones')),2)

    def test_tiempos_cortos_no_se_redondean(self):
        self.prestar(2)
        with self.app.app_context():
            sistema=cargar_dominio()
            r=Remito(1,1,1,1,2,'ida','recibido','bueno')
            for estado,fecha in [('pendiente','2026-01-01T08:00:00'),('empaquetado','2026-01-01T08:00:30'),('despachado','2026-01-01T09:00:00'),('recibido','2026-01-01T09:00:10.357802')]:
                r.recuperar_cambio(estado,fecha,'')
            sistema.remitos[0]=r
            # Fija la fecha de la entrada original en el fixture: guardar_dominio no altera históricos.
            db.session.get(HistorialFila,(1,0)).fecha='2026-01-01T08:00:00'
            guardar_dominio(sistema)
            db.session.commit()
        fila=self.get('reportes/movimientos?desde=2026-01-01&hasta=2026-01-01')[0]
        self.assertAlmostEqual(fila['promedio_segundos_transito'],10.357802)
        self.assertEqual(fila['tasa_envios_exitosos'],100)
        self.assertEqual(self.get('reportes/movimientos?desde=2026-01-02'),[])

    def test_inventario_estados_excluyentes_y_reportes_vacios(self):
        fila=self.get('reportes/disponibilidad')['detalle'][0]
        categorias=['propios_disponibles','propios_comprometidos','propios_prestados','propios_en_transito','propios_fuera_servicio','propios_en_reparacion','propios_extraviados']
        self.assertEqual(sum(fila[k] for k in categorias),fila['propios'])
        for reporte in ('prestamos','solicitados','movimientos'):
            r=self.get('reportes/'+reporte)
            self.assertIsNotNone(r)
        self.prestar()
        fila=self.get('reportes/disponibilidad')['detalle'][0]
        self.assertEqual(fila['propios_prestados'],1)
        self.assertEqual(fila['propios_comprometidos'],0)
        self.assertEqual(sum(fila[k] for k in categorias),fila['propios'])

    def test_api_selecciona_los_cuatro_reportes_directamente(self):
        for tipo, clase in list(REPORTES.items()):
            constructor = Mock(wraps=clase)
            with patch.dict(REPORTES, {tipo: constructor}):
                self.get('reportes/'+tipo)
                constructor.assert_called_once_with()

    def test_vigentes_vencidos_y_multas(self):
        self.prestar()
        reporte=self.get('reportes/prestamos')
        self.assertEqual(reporte['detalle'][0]['dias_atraso'],0)
        self.assertEqual(reporte['detalle'][0]['multa'],0)
        self.assertIn('el pago no se registra',reporte['aclaracion'])
        with self.app.app_context():
            p=db.session.get(PrestamoFila,1)
            p.vencimiento=(date.today()-timedelta(days=2)).isoformat()
            db.session.commit()
        self.assertEqual(self.get('reportes/prestamos')['detalle'][0]['dias_atraso'],2)
        self.assertEqual(self.get('reportes/prestamos')['detalle'][0]['multa'],1000)
        # Un préstamo activo figura siempre: el período solo filtra los ya devueltos.
        self.assertEqual(len(self.get('reportes/prestamos?desde=1900-01-01&hasta=1900-01-01')['detalle']),1)
        self.post('/devoluciones',prestamo_id=1,sede_id=1,condicion='bueno')
        self.assertEqual(self.get('reportes/prestamos?desde=1900-01-01&hasta=1900-01-01')['detalle'],[])
        self.assertEqual(self.get('reportes/prestamos')['detalle'][0]['multa'],1000)

    def test_entrega_no_se_pierde_al_reiniciar(self):
        from biblioteca.web import crear_app
        self.prestar()
        antes=self.get('estado')
        otra=crear_app(self.config)
        with otra.app_context():
            cliente=iniciar_sesion(otra.test_client())
            self.assertEqual(cliente.get('/api/estado').json,antes)
            self.assertEqual(cliente.post('/api/devoluciones',json={
                'prestamo_id':1,'sede_id':1,'condicion':'bueno'}).status_code,201)
            db.session.remove()
            db.engine.dispose()
        self.assertEqual(self.get('prestamos')[0]['estado'],'devuelto')

    def test_devolucion_no_puede_preceder_inicio_futuro(self):
        self.prestar()
        with self.app.app_context():
            db.session.get(PrestamoFila,1).inicio=(datetime.now()+timedelta(days=1)).isoformat()
            db.session.commit()
        antes=self.get('estado')
        self.post('/devoluciones',esperado=400,prestamo_id=1,sede_id=1,condicion='bueno')
        self.assertEqual(self.get('estado'),antes)

    def test_inventario_explica_sede_dada_de_baja(self):
        self.assertEqual(self.cliente.patch('/api/sedes/1',json={'activa':False}).status_code,200)
        fila=self.get('disponibilidad?libro_id=1&sede_id=1&modo=todos')[0]
        self.assertFalse(fila['disponible'])
        self.assertIn('dada de baja',fila['motivo'])
        self.assertEqual(self.get('disponibilidad?libro_id=1&sede_id=1'),[])

    def test_carga_ejemplos_comparte_dominio_y_no_duplica(self):
        from cargar_ejemplos import agregar_datos_prueba
        with self.app.app_context():
            sistema=cargar_dominio()
            cantidades=agregar_datos_prueba(sistema)
            self.assertGreater(cantidades['libros'],0)
            guardar_dominio(sistema)
            db.session.commit()
            segunda=agregar_datos_prueba(cargar_dominio())
            self.assertTrue(all(valor==0 for valor in segunda.values()))
        self.assertEqual(len(self.get('libros')),11)


if __name__=='__main__':
    unittest.main()
