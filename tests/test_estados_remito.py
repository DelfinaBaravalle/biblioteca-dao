"""State y su integración con Observer y persistencia ORM aislada."""
import tempfile
import unittest
from pathlib import Path

from biblioteca.estados_remito import EstadoRemito, Pendiente, Empaquetado, Despachado, Recibido
from biblioteca.modelos import Remito
from biblioteca.observadores import ObservadorRemito
from biblioteca.orm import db, guardar_dominio, cargar_dominio
from biblioteca.sistema import Biblioteca
from biblioteca.web import crear_app


class ObservadorDePrueba(ObservadorRemito):
    def __init__(self):
        self.eventos = []

    def actualizar(self, remito, observacion):
        self.eventos.append((remito.estado, observacion))


class PruebasStateRemito(unittest.TestCase):
    def test_contexto_delega_en_estados_concretos_y_notifica(self):
        remito = Remito(1, 1, 1, 1, 2, 'ida')
        remito.notificar('Creación del remito')
        observador = ObservadorDePrueba()
        remito.suscribir(observador)
        self.assertIsInstance(remito._estado, Pendiente)
        for numero, (accion, tipo) in enumerate([
                ('empaquetar', Empaquetado), ('despachar', Despachado), ('recibir', Recibido)], 1):
            remito.avanzar(accion, ' Control ')
            self.assertIsInstance(remito._estado, tipo)
            self.assertEqual(remito.estado, tipo.nombre)
            self.assertEqual(remito.a_fila()[6], tipo.nombre)
            self.assertEqual(len(remito.consultar_historial()), numero + 1)
        self.assertEqual(observador.eventos,
                         [('empaquetado', 'Control'), ('despachado', 'Control'), ('recibido', 'Control')])

    def test_acciones_invalidas_no_cambian_estado_ni_historial(self):
        for tipo, permitida in [(Pendiente, 'empaquetar'), (Empaquetado, 'despachar'),
                                (Despachado, 'recibir'), (Recibido, None)]:
            for accion in ['empaquetar', 'despachar', 'recibir', 'desconocida']:
                if accion == permitida:
                    continue
                with self.subTest(estado=tipo.nombre, accion=accion):
                    remito = Remito(1, 1, 1, 1, 2, 'ida', tipo.nombre)
                    observador = ObservadorDePrueba()
                    remito.suscribir(observador)
                    anterior = remito._estado
                    with self.assertRaises(ValueError):
                        remito.avanzar(accion)
                    self.assertIs(remito._estado, anterior)
                    self.assertEqual(remito.consultar_historial(), [])
                    self.assertEqual(observador.eventos, [])

    def test_recuperacion_orm_reconstruye_state_sin_duplicar_eventos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            app = crear_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI':
                             'sqlite:///' + str(Path(carpeta) / 'estados.sqlite')})
            with app.app_context():
                try:
                    sistema = Biblioteca()
                    for nombre in ('Centro', 'Norte'):
                        sistema.agregar_sede(nombre, 'Calle 1', '111', '8 a 18')
                    sistema.agregar_socio('123', 'Ana', 'Contacto')
                    sistema.agregar_libro('A', 'Libro', 'Autora')
                    sistema.agregar_ejemplar('E1', 1, 1)
                    sistema.prestar(1, 1, 1, 2)
                    guardar_dominio(sistema)
                    db.session.commit()
                    for numero, (tipo, accion) in enumerate([
                            (Pendiente, 'empaquetar'), (Empaquetado, 'despachar'),
                            (Despachado, 'recibir'), (Recibido, None)], 1):
                        db.session.remove()
                        copia = cargar_dominio()
                        remito = copia.remitos[0]
                        self.assertIsInstance(remito._estado, tipo)
                        self.assertEqual(len(remito.consultar_historial()), numero)
                        if accion:
                            condicion = 'bueno' if accion == 'recibir' else None
                            copia.avanzar_remito(1, accion, condicion=condicion)
                            guardar_dominio(copia)
                            db.session.commit()
                    self.assertTrue(copia.prestamos[0].estado.es('listo_retiro'))
                finally:
                    db.session.remove()
                    db.engine.dispose()

    def test_estado_desconocido_se_rechaza(self):
        with self.assertRaises(ValueError):
            Remito(1, 1, 1, 1, 2, 'ida', 'inexistente')

    def test_tipo_de_remito_desconocido_se_rechaza(self):
        with self.assertRaises(ValueError):
            Remito(1, 1, 1, 1, 2, 'devolucion')

    def test_interfaz_state_es_abstracta(self):
        with self.assertRaises(TypeError):
            EstadoRemito()


if __name__ == '__main__':
    unittest.main()
