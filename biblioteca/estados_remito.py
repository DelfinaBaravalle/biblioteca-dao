"""State: cada estado decide qué acción admite y cuál es el siguiente estado."""
from abc import ABC, abstractmethod


class EstadoRemito(ABC):
    def validar_accion(self, accion, permitidas):
        if accion not in permitidas:
            raise ValueError(f"Un remito {self.nombre} solo admite: {', '.join(permitidas)}.")

    @abstractmethod
    def avanzar(self, accion):
        """Devuelve el próximo estado, sin modificar el contexto ni notificar."""
        pass


class Pendiente(EstadoRemito):
    nombre = "pendiente"

    def avanzar(self, accion):
        self.validar_accion(accion, ("empaquetar", "cancelar"))
        if accion == "cancelar":
            return Cancelado()
        return Empaquetado()


class Empaquetado(EstadoRemito):
    nombre = "empaquetado"

    def avanzar(self, accion):
        self.validar_accion(accion, ("despachar", "cancelar"))
        if accion == "cancelar":
            return Cancelado()
        return Despachado()


class Despachado(EstadoRemito):
    nombre = "despachado"

    def avanzar(self, accion):
        self.validar_accion(accion, ("recibir", "informar_extravio"))
        if accion == "informar_extravio":
            return Extraviado()
        return Recibido()


class Recibido(EstadoRemito):
    nombre = "recibido"

    def avanzar(self, accion):
        raise ValueError("El remito ya fue recibido.")


class Extraviado(EstadoRemito):
    nombre = "extraviado"

    def avanzar(self, accion):
        raise ValueError("El remito fue informado como extraviado.")


class Cancelado(EstadoRemito):
    nombre = "cancelado"

    def avanzar(self, accion):
        raise ValueError("El remito está cancelado.")
