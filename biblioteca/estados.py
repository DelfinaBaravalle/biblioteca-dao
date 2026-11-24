"""Clase Estado (Vista 3): nombre y ámbito de los estados de cada entidad.

Ejemplar, Prestamo, Solicitud, Reserva y Reparacion guardan estado_id.
El Remito no usa esta clase: su ciclo de vida se modela con el patrón State.
"""


class Estado:
    def __init__(self, id, nombre, ambito):
        self.id = id
        self.nombre = nombre
        self.ambito = ambito

    def es(self, nombre):
        return self.nombre == nombre

    def es_ambito(self, ambito):
        return self.ambito == ambito

    def a_fila(self):
        return (self.id, self.nombre, self.ambito)


# Estados por ámbito, en el orden del documento entregado. Los ID son fijos.
ESTADOS_POR_AMBITO = {
    "Ejemplar": ("disponible", "comprometido", "prestado", "en_transito",
                 "fuera_servicio", "en_reparacion", "extraviado"),
    "Prestamo": ("esperando_envio", "listo_retiro", "activo", "retornando",
                 "devuelto", "cancelado"),
    "Solicitud": ("pendiente", "asignada", "cancelada"),
    "Reserva": ("pendiente", "atendida", "cancelada"),
    "Reparacion": ("abierta", "cerrada"),
}


def crear_catalogo():
    estados = []
    for ambito, nombres in ESTADOS_POR_AMBITO.items():
        for nombre in nombres:
            estados.append(Estado(len(estados) + 1, nombre, ambito))
    return estados


ESTADOS = crear_catalogo()


def obtener_estado(estado_id):
    for estado in ESTADOS:
        if estado.id == estado_id:
            return estado
    raise ValueError(f"No existe el estado con ID {estado_id}.")


def id_estado(ambito, nombre):
    for estado in ESTADOS:
        if estado.es_ambito(ambito) and estado.es(nombre):
            return estado.id
    raise ValueError(f"El estado {nombre} no corresponde a {ambito}.")


def validar_estado(estado_id, ambito):
    """Impide asignar a una entidad un estado de otro ámbito."""
    estado = obtener_estado(estado_id)
    if not estado.es_ambito(ambito):
        raise ValueError(f"El estado {estado.nombre} es de {estado.ambito}, no de {ambito}.")
    return estado_id
