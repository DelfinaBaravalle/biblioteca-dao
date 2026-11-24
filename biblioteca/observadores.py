"""Observer: el remito notifica y su historial registra cada cambio."""
from abc import ABC, abstractmethod
from datetime import datetime


class ObservadorRemito(ABC):
    @abstractmethod
    def actualizar(self, remito, observacion):
        pass


class HistorialRemito(ObservadorRemito):
    def __init__(self):
        self._cambios = []

    def actualizar(self, remito, observacion):
        self.agregar(remito.estado, datetime.now().isoformat(), observacion)

    def agregar(self, estado, fecha, observacion):
        self._cambios.append({"estado": estado, "fecha": fecha, "observacion": observacion})

    def consultar(self):
        return [dict(cambio) for cambio in self._cambios]
