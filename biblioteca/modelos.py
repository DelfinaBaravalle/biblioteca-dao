"""Entidades de la biblioteca: constructores, propiedades y métodos propios."""
from datetime import date, datetime, timedelta

from .observadores import HistorialRemito
from .estados_remito import (Pendiente, Empaquetado, Despachado, Recibido,
                             Extraviado, Cancelado)
from .estados import obtener_estado, id_estado, validar_estado


def validar_texto(valor):
    if not isinstance(valor, str):
        raise ValueError("Ingrese un campo de texto válido.")
    if len(valor) > 500 or any(ord(c) < 32 for c in valor):
        raise ValueError("El texto admite hasta 500 caracteres sin caracteres de control.")
    valor = valor.strip()
    if not valor:
        raise ValueError("Los campos de texto no pueden quedar vacíos.")
    return valor


# Condiciones físicas, de mejor a peor.
CONDICIONES = ("bueno", "dañado", "inutilizable")


def validar_condicion(condicion):
    if condicion not in CONDICIONES:
        raise ValueError("Condición válida: bueno, dañado o inutilizable.")


# La base guarda las fechas como texto ISO; el dominio trabaja con date y datetime.


def a_fecha(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(valor[:10])


def a_fecha_hora(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    if isinstance(valor, date):
        return datetime(valor.year, valor.month, valor.day)
    return datetime.fromisoformat(valor)


def a_texto(valor):
    return None if valor is None else valor.isoformat()


class Sede:
    def __init__(self, id, nombre, direccion, contacto, horarios, activa=True):
        self.id = id
        self.nombre = validar_texto(nombre)
        self.direccion = validar_texto(direccion)
        self.contacto = validar_texto(contacto)
        self.horarios = validar_texto(horarios)
        self.activa = bool(activa)

    def verificar_activa(self):
        if not self.activa:
            raise ValueError("La sede está dada de baja.")

    def a_fila(self):
        return (self.id, self.nombre, self.direccion, self.contacto, self.horarios, self.activa)


class Socio:
    def __init__(self, id, dni, nombre, contacto, habilitado=True):
        self.id = id
        dni = validar_texto(dni)
        if not dni.isascii() or not dni.isdigit() or len(dni) > 10 or int(dni) == 0:
            raise ValueError("El DNI debe contener entre 1 y 10 dígitos y ser mayor que cero.")
        self._dni = str(int(dni))
        self.nombre = validar_texto(nombre)
        self.contacto = validar_texto(contacto)
        self.habilitado = bool(habilitado)

    @property
    def dni(self):
        return self._dni

    def verificar_habilitado(self):
        if not self.habilitado:
            raise ValueError("El socio está inhabilitado.")

    def a_fila(self):
        return (self.id, self.dni, self.nombre, self.contacto, self.habilitado)


class Libro:
    def __init__(self, id, isbn, titulo, autor):
        self.id = id
        self._isbn = validar_texto(isbn.replace("-", "").replace(" ", "").upper())
        self.titulo = validar_texto(titulo)
        self.autor = validar_texto(autor)

    @property
    def isbn(self):
        return self._isbn

    def a_fila(self):
        return (self.id, self.isbn, self.titulo, self.autor)


class Ejemplar:
    def __init__(self, id, codigo, libro_id, sede_id, ubicacion_id,
                 estado_id=None, condicion="bueno"):
        self.id = id
        self._codigo = validar_texto(codigo).upper()
        self.libro_id = libro_id
        self.sede_id = sede_id
        self.ubicacion_id = ubicacion_id
        self.estado_id = estado_id if estado_id is not None else id_estado("Ejemplar", "disponible")
        validar_condicion(condicion)
        self._condicion = condicion

    @property
    def estado_id(self):
        return self._estado_id

    @estado_id.setter
    def estado_id(self, valor):
        self._estado_id = validar_estado(valor, "Ejemplar")

    @property
    def estado(self):
        return obtener_estado(self._estado_id)

    @property
    def codigo(self):
        return self._codigo

    @property
    def condicion(self):
        return self._condicion

    @condicion.setter
    def condicion(self, valor):
        validar_condicion(valor)
        self._condicion = valor

    def esta_disponible(self, sede_id):
        return (self.sede_id == sede_id and self.ubicacion_id == sede_id
                and self.estado.es("disponible") and self.condicion == "bueno")

    def cambiar_condicion(self, condicion):
        validar_condicion(condicion)
        if not (self.estado.es("disponible") or self.estado.es("fuera_servicio")):
            raise ValueError("El ejemplar tiene una operación pendiente.")
        if self.condicion != "bueno" and condicion == "bueno":
            raise ValueError("Para recuperar material dañado debe finalizar una reparación.")
        self.condicion = condicion
        nombre = "disponible" if condicion == "bueno" else "fuera_servicio"
        self.estado_id = id_estado("Ejemplar", nombre)

    def a_fila(self):
        return (self.id, self.codigo, self.libro_id, self.sede_id,
                self.ubicacion_id, self.estado_id, self.condicion)


class Prestamo:
    def __init__(self, id, socio_id, ejemplar_id, origen_id, destino_id, fecha_solicitud,
                 estado_id, inicio=None, vencimiento=None):
        self.id = id
        self.socio_id = socio_id
        self.ejemplar_id = ejemplar_id
        self.origen_id = origen_id
        self.destino_id = destino_id
        self.fecha_solicitud = a_fecha(fecha_solicitud)
        self.estado_id = estado_id
        self.inicio = a_fecha_hora(inicio)
        self.vencimiento = a_fecha(vencimiento)

    @property
    def estado_id(self):
        return self._estado_id

    @estado_id.setter
    def estado_id(self, valor):
        self._estado_id = validar_estado(valor, "Prestamo")

    @property
    def estado(self):
        return obtener_estado(self._estado_id)

    @property
    def vencido(self):
        return (self.estado.es("activo") and self.vencimiento is not None
                and self.vencimiento < date.today())

    def activar(self, dias):
        self.estado_id = id_estado("Prestamo", "activo")
        self.inicio = datetime.now()
        self.vencimiento = date.today() + timedelta(days=dias)

    def dias_atraso(self, fecha_corte):
        """Días posteriores al vencimiento hasta fecha_corte; nunca negativo."""
        if self.vencimiento is None:
            return 0
        return max(0, (a_fecha(fecha_corte) - self.vencimiento).days)

    def multa(self, tarifa_diaria, fecha_corte=None):
        """Sin fecha de corte se calcula a hoy; para un préstamo devuelto se pasa la fecha de la devolución."""
        if fecha_corte is None:
            fecha_corte = date.today()
        return self.dias_atraso(fecha_corte) * tarifa_diaria

    def a_fila(self):
        return (self.id, self.socio_id, self.ejemplar_id, self.origen_id, self.destino_id,
                a_texto(self.fecha_solicitud), self.estado_id, a_texto(self.inicio),
                a_texto(self.vencimiento))


class Reserva:
    def __init__(self, id, socio_id, libro_id, sede_id, fecha, estado_id=None):
        self.id = id
        self.socio_id = socio_id
        self.libro_id = libro_id
        self.sede_id = sede_id
        self.fecha = a_fecha_hora(fecha)
        self.estado_id = estado_id if estado_id is not None else id_estado("Reserva", "pendiente")

    @property
    def estado_id(self):
        return self._estado_id

    @estado_id.setter
    def estado_id(self, valor):
        self._estado_id = validar_estado(valor, "Reserva")

    @property
    def estado(self):
        return obtener_estado(self._estado_id)

    def cancelar(self):
        if not self.estado.es("pendiente"):
            raise ValueError("La reserva ya está cerrada.")
        self.estado_id = id_estado("Reserva", "cancelada")

    def a_fila(self):
        return (self.id, self.socio_id, self.libro_id, self.sede_id, a_texto(self.fecha),
                self.estado_id)


class Remito:
    def __init__(self, id, prestamo_id, ejemplar_id, origen_id, destino_id, tipo,
                 estado="pendiente", condicion_recepcion=None):
        self.id = id
        self.prestamo_id = prestamo_id
        self.ejemplar_id = ejemplar_id
        self.origen_id = origen_id
        self.destino_id = destino_id
        if tipo not in ("ida", "retorno"):
            raise ValueError("El tipo de remito debe ser ida o retorno.")
        self.tipo = tipo
        self.condicion_recepcion = condicion_recepcion
        # Reconstruye el objeto State desde el nombre persistido, sin emitir eventos.
        estados = {"pendiente": Pendiente, "empaquetado": Empaquetado,
                   "despachado": Despachado, "recibido": Recibido,
                   "extraviado": Extraviado, "cancelado": Cancelado}
        if estado not in estados:
            raise ValueError("Estado de remito inválido.")
        self._estado = estados[estado]()
        self._observadores = []
        self._registro = HistorialRemito()
        self.suscribir(self._registro)

    @property
    def estado(self):
        return self._estado.nombre

    @property
    def condicion_recepcion(self):
        return self._condicion_recepcion

    @condicion_recepcion.setter
    def condicion_recepcion(self, valor):
        # Queda vacía hasta que el remito se recibe.
        if valor is not None:
            validar_condicion(valor)
        self._condicion_recepcion = valor

    def consultar_historial(self):
        return self._registro.consultar()

    def recuperar_cambio(self, estado, fecha, observacion):
        """Recupera una entrada guardada sin generar otra notificación."""
        self._registro.agregar(estado, fecha, observacion)

    def suscribir(self, observador):
        if observador not in self._observadores:
            self._observadores.append(observador)

    def desuscribir(self, observador):
        self._observadores.remove(observador)

    def notificar(self, observacion):
        for observador in self._observadores:
            observador.actualizar(self, observacion)

    def avanzar(self, accion, observacion=""):
        observacion = observacion.strip()
        # Solo los remitos de ida pueden cancelarse; el estado no conoce el tipo de viaje.
        if accion == "cancelar" and self.tipo != "ida":
            raise ValueError("Solo se puede cancelar un remito de ida.")
        self._estado = self._estado.avanzar(accion)
        self.notificar(observacion)

    def a_fila(self):
        return (self.id, self.prestamo_id, self.ejemplar_id, self.origen_id,
                self.destino_id, self.tipo, self.estado, self.condicion_recepcion)


class Solicitud:
    def __init__(self, id, socio_id, libro_id, origen_id, destino_id, fecha,
                 estado_id=None, prestamo_id=None):
        self.id = id
        self.socio_id = socio_id
        self.libro_id = libro_id
        self.origen_id = origen_id
        self.destino_id = destino_id
        self.fecha = a_fecha_hora(fecha)
        self.estado_id = estado_id if estado_id is not None else id_estado("Solicitud", "pendiente")
        self.prestamo_id = prestamo_id

    @property
    def estado_id(self):
        return self._estado_id

    @estado_id.setter
    def estado_id(self, valor):
        self._estado_id = validar_estado(valor, "Solicitud")

    @property
    def estado(self):
        return obtener_estado(self._estado_id)

    def a_fila(self):
        return (self.id, self.socio_id, self.libro_id, self.origen_id,
                self.destino_id, a_texto(self.fecha), self.estado_id, self.prestamo_id)


class Devolucion:
    def __init__(self, id, prestamo_id, sede_id, fecha, condicion):
        self.id = id
        self.prestamo_id = prestamo_id
        self.sede_id = sede_id
        self.fecha = a_fecha_hora(fecha)
        validar_condicion(condicion)
        self.condicion = condicion

    def a_fila(self):
        return (self.id, self.prestamo_id, self.sede_id, a_texto(self.fecha), self.condicion)


class Reparacion:
    def __init__(self, id, ejemplar_id, descripcion, inicio, estado_id=None,
                 fin=None, resultado=""):
        self.id = id
        self.ejemplar_id = ejemplar_id
        self.descripcion = validar_texto(descripcion)
        self.inicio = a_fecha_hora(inicio)
        self.estado_id = estado_id if estado_id is not None else id_estado("Reparacion", "abierta")
        self.fin = a_fecha_hora(fin)
        self.resultado = resultado

    @property
    def estado_id(self):
        return self._estado_id

    @estado_id.setter
    def estado_id(self, valor):
        self._estado_id = validar_estado(valor, "Reparacion")

    @property
    def estado(self):
        return obtener_estado(self._estado_id)

    def a_fila(self):
        return (self.id, self.ejemplar_id, self.descripcion, a_texto(self.inicio),
                self.estado_id, a_texto(self.fin), self.resultado)


class Entrega:
    def __init__(self, id, prestamo_id, fecha):
        self.id = id
        self.prestamo_id = prestamo_id
        self.fecha = a_fecha_hora(fecha)

    def a_fila(self):
        return (self.id, self.prestamo_id, a_texto(self.fecha))
