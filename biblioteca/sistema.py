from datetime import date, datetime

from .modelos import Sede, Socio, Libro, Ejemplar, Prestamo, Reserva, Remito
from .modelos import validar_texto, validar_condicion, CONDICIONES, Solicitud, Devolucion, Reparacion, Entrega
from .estados import ESTADOS, id_estado
from .validaciones import validar_nombre, validar_contacto


class Biblioteca:
    DIAS_PRESTAMO = 14
    # Tarifa diaria configurable: $500 por día de atraso (decisión del grupo).
    MULTA_DIARIA = 500.0
    REMITOS_FINALIZADOS = ("recibido", "extraviado", "cancelado")
    TIPOS = {"sedes": Sede, "socios": Socio, "libros": Libro,
             "ejemplares": Ejemplar, "prestamos": Prestamo,
             "reservas": Reserva, "remitos": Remito, "solicitudes": Solicitud,
             "devoluciones": Devolucion, "reparaciones": Reparacion, "entregas": Entrega}

    def __init__(self):
        self.sedes = []
        self.socios = []
        self.libros = []
        self.ejemplares = []
        self.prestamos = []
        self.reservas = []
        self.remitos = []
        self.solicitudes = []
        self.devoluciones = []
        self.reparaciones = []
        self.entregas = []
        # Catálogo de estados (Vista 3); no se guarda como colección editable.
        self.estados = list(ESTADOS)

    def colecciones(self):
        return {"sedes": self.sedes, "socios": self.socios, "libros": self.libros,
                "ejemplares": self.ejemplares, "prestamos": self.prestamos,
                "reservas": self.reservas, "remitos": self.remitos,
                "solicitudes": self.solicitudes, "devoluciones": self.devoluciones,
                "reparaciones": self.reparaciones, "entregas": self.entregas}

    def buscar(self, coleccion, identificador):
        for objeto in self.colecciones()[coleccion]:
            if objeto.id == identificador:
                return objeto
        raise ValueError(f"No existe el ID {identificador} en {coleccion}.")

    def _id(self, coleccion):
        return max((objeto.id for objeto in self.colecciones()[coleccion]), default=0) + 1

    def _unico(self, coleccion, atributo, valor, excluir=None):
        for objeto in self.colecciones()[coleccion]:
            if objeto.id != excluir and getattr(objeto, atributo).lower() == valor.lower():
                raise ValueError(f"Ya existe {atributo}: {valor}.")

    def _abierto(self, prestamo):
        """Un préstamo devuelto o cancelado ya no tiene operaciones pendientes."""
        return not (prestamo.estado.es("devuelto") or prestamo.estado.es("cancelado"))

    def _prestamo_en_curso(self, reserva):
        """Préstamo abierto del socio de la reserva, por ese libro y hacia esa sede de retiro."""
        for p in self.prestamos:
            if (p.socio_id == reserva.socio_id and p.destino_id == reserva.sede_id and self._abierto(p)
                    and self.buscar("ejemplares", p.ejemplar_id).libro_id == reserva.libro_id):
                return p
        return None

    def _en_espera(self, reserva):
        """Una reserva pendiente espera turno salvo que su socio ya tenga el préstamo en curso."""
        return reserva.estado.es("pendiente") and self._prestamo_en_curso(reserva) is None

    def _sede(self, identificador):
        sede = self.buscar("sedes", identificador)
        sede.verificar_activa()
        return sede

    def _socio(self, identificador):
        socio = self.buscar("socios", identificador)
        socio.verificar_habilitado()
        if any(p.socio_id == identificador and p.vencido for p in self.prestamos):
            raise ValueError("El socio tiene préstamos vencidos.")
        return socio

    def agregar_sede(self, nombre, direccion, contacto, horarios):
        sede = Sede(self._id("sedes"), nombre, direccion, contacto, horarios)
        validar_nombre(sede.nombre)
        validar_contacto(sede.contacto)
        self._unico("sedes", "nombre", sede.nombre)
        self.sedes.append(sede)
        return sede

    def agregar_socio(self, dni, nombre, contacto):
        socio = Socio(self._id("socios"), dni, nombre, contacto)
        validar_nombre(socio.nombre)
        validar_contacto(socio.contacto)
        self._unico("socios", "dni", socio.dni)
        self.socios.append(socio)
        return socio

    def agregar_libro(self, isbn, titulo, autor):
        libro = Libro(self._id("libros"), isbn, titulo, autor)
        self._unico("libros", "isbn", libro.isbn)
        self.libros.append(libro)
        return libro

    def agregar_ejemplar(self, codigo, libro_id, sede_id):
        self.buscar("libros", libro_id)
        self._sede(sede_id)
        ejemplar = Ejemplar(self._id("ejemplares"), codigo, libro_id, sede_id, sede_id)
        self._unico("ejemplares", "codigo", ejemplar.codigo)
        self.ejemplares.append(ejemplar)
        return ejemplar

    def editar(self, coleccion, identificador, **cambios):
        permitidos = {"sedes": {"nombre", "direccion", "contacto", "horarios"},
                      "socios": {"nombre", "contacto"},
                      "libros": {"titulo", "autor"}}
        if coleccion not in permitidos or not set(cambios) <= permitidos[coleccion]:
            raise ValueError("Campos de edición no permitidos.")
        objeto = self.buscar(coleccion, identificador)
        cambios = {campo: validar_texto(valor) for campo, valor in cambios.items()}
        if "nombre" in cambios:
            validar_nombre(cambios["nombre"])
        if "contacto" in cambios:
            validar_contacto(cambios["contacto"])
        if coleccion == "sedes" and "nombre" in cambios:
            self._unico("sedes", "nombre", cambios["nombre"], identificador)
        for campo, valor in cambios.items():
            setattr(objeto, campo, valor)

    def cambiar_sede(self, sede_id, activa):
        sede = self.buscar("sedes", sede_id)
        if not activa:
            if any(self._abierto(p) and sede_id in (p.origen_id, p.destino_id)
                   for p in self.prestamos):
                raise ValueError("La sede tiene préstamos o retornos pendientes.")
            if any(r.estado.es("pendiente") and r.sede_id == sede_id for r in self.reservas):
                raise ValueError("La sede tiene reservas pendientes.")
            if any(s.estado.es("pendiente") and sede_id in (s.origen_id, s.destino_id)
                   for s in self.solicitudes):
                raise ValueError("La sede tiene solicitudes pendientes.")
            if any(r.estado not in self.REMITOS_FINALIZADOS and sede_id in (r.origen_id, r.destino_id)
                   for r in self.remitos):
                raise ValueError("La sede tiene movimientos pendientes.")
        sede.activa = activa

    def cambiar_socio(self, socio_id, habilitado):
        self.buscar("socios", socio_id).habilitado = habilitado

    def cambiar_condicion(self, ejemplar_id, condicion):
        self.buscar("ejemplares", ejemplar_id).cambiar_condicion(condicion)

    def disponibles(self, libro_id, sede_id):
        self.buscar("libros", libro_id)
        self._sede(sede_id)
        return [ejemplar for ejemplar in self.ejemplares
                if ejemplar.libro_id == libro_id and ejemplar.esta_disponible(sede_id)]

    def consultar_ejemplares(self, libro_id, sede_id):
        self.buscar("libros", libro_id)
        sede = self.buscar("sedes", sede_id)
        resultados = []
        for ejemplar in self.ejemplares:
            if ejemplar.libro_id != libro_id or sede_id not in (ejemplar.sede_id, ejemplar.ubicacion_id):
                continue
            motivos = []
            if not sede.activa:
                motivos.append("La sede consultada está dada de baja.")
            if ejemplar.sede_id != sede_id:
                motivos.append("Pertenece a otra sede; solicite el préstamo desde su propietaria.")
            if ejemplar.ubicacion_id is None:
                motivos.append("No tiene ubicación registrada.")
            elif ejemplar.ubicacion_id != sede_id:
                motivos.append("Se encuentra en otra sede.")
            if not ejemplar.estado.es("disponible"):
                motivos.append({"comprometido": "Está comprometido para un envío, retiro o retorno.",
                                "prestado": "Está entregado a un socio.",
                                "en_reparacion": "Tiene una reparación abierta.",
                                "fuera_servicio": "Está fuera de servicio.",
                                "en_transito": "Tiene un remito en tránsito.",
                                "extraviado": "Fue informado como extraviado."}.get(
                                    ejemplar.estado.nombre, "Estado operativo no disponible."))
            if ejemplar.condicion != "bueno":
                motivos.append("La condición física es " + ejemplar.condicion + ".")
            resultados.append((ejemplar, not motivos, " ".join(motivos) or "Disponible para asignar; se controla FIFO al prestar."))
        return resultados

    def reservar(self, socio_id, libro_id, sede_id):
        self._socio(socio_id)
        self._sede(sede_id)
        self.buscar("libros", libro_id)
        if any(r.socio_id == socio_id and r.libro_id == libro_id
               and r.sede_id == sede_id and r.estado.es("pendiente") for r in self.reservas):
            raise ValueError("El socio ya tiene esa reserva pendiente.")
        reserva = Reserva(self._id("reservas"), socio_id, libro_id, sede_id,
                          datetime.now().replace(microsecond=0))
        self.reservas.append(reserva)
        return reserva

    def cancelar_reserva(self, reserva_id):
        self.buscar("reservas", reserva_id).cancelar()

    def prestar(self, socio_id, ejemplar_id, origen_id, destino_id):
        self._socio(socio_id)
        self._sede(origen_id)
        self._sede(destino_id)
        ejemplar = self.buscar("ejemplares", ejemplar_id)
        if ejemplar.sede_id != origen_id or ejemplar.ubicacion_id != origen_id:
            raise ValueError("El ejemplar debe pertenecer y estar en la sede de origen.")
        if not ejemplar.estado.es("disponible") or ejemplar.condicion != "bueno":
            raise ValueError("El ejemplar no está disponible.")
        if any(p.socio_id == socio_id and self._abierto(p)
               and self.buscar("ejemplares", p.ejemplar_id).libro_id == ejemplar.libro_id
               for p in self.prestamos):
            raise ValueError("El socio ya tiene una operación de préstamo pendiente para ese libro.")
        cola = [r for r in self.reservas if r.libro_id == ejemplar.libro_id
                and r.sede_id == destino_id and self._en_espera(r)]
        primera = min(cola, key=lambda r: r.id) if cola else None
        if primera and primera.socio_id != socio_id:
            raise ValueError("Otro socio tiene prioridad por reserva en la sede destino.")
        prestamo = Prestamo(self._id("prestamos"), socio_id, ejemplar_id,
                            origen_id, destino_id, date.today(), id_estado("Prestamo", "esperando_envio"))
        self.prestamos.append(prestamo)
        ejemplar.estado_id = id_estado("Ejemplar", "comprometido")
        if origen_id == destino_id:
            prestamo.estado_id = id_estado("Prestamo", "listo_retiro")
        else:
            self._crear_remito(prestamo, origen_id, destino_id, "ida")
        return prestamo

    def _liberar(self, ejemplar):
        """Sin operaciones pendientes, el ejemplar queda disponible o fuera de servicio según su condición."""
        nombre = "disponible" if ejemplar.condicion == "bueno" else "fuera_servicio"
        ejemplar.estado_id = id_estado("Ejemplar", nombre)

    def _activar(self, prestamo):
        prestamo.activar(self.DIAS_PRESTAMO)
        self.buscar("ejemplares", prestamo.ejemplar_id).estado_id = id_estado("Ejemplar", "prestado")

    def entregar(self, prestamo_id):
        prestamo = self.buscar("prestamos", prestamo_id)
        if any(e.prestamo_id == prestamo_id for e in self.entregas):
            raise ValueError("La entrega ya está registrada.")
        self._socio(prestamo.socio_id)
        self._sede(prestamo.origen_id)
        self._sede(prestamo.destino_id)
        ejemplar = self.buscar("ejemplares", prestamo.ejemplar_id)
        if not prestamo.estado.es("listo_retiro"):
            raise ValueError("El préstamo debe estar listo para retirar; reciba primero el remito de ida.")
        if ejemplar.ubicacion_id != prestamo.destino_id or ejemplar.condicion != "bueno":
            raise ValueError("El ejemplar no está en condiciones de entregarse en la sede de retiro.")
        if not ejemplar.estado.es("comprometido"):
            raise ValueError("El ejemplar no está comprometido para esta entrega.")
        self._activar(prestamo)
        self.entregas.append(Entrega(self._id("entregas"), prestamo.id, datetime.now()))
        # La reserva se atiende recién cuando el socio recibe el libro: si el préstamo
        # se cancela antes (envío cancelado, extraviado o dañado), conserva su lugar.
        for reserva in self.reservas:
            if reserva.estado.es("pendiente") and self._prestamo_en_curso(reserva) is prestamo:
                reserva.estado_id = id_estado("Reserva", "atendida")
        return prestamo

    def _crear_remito(self, prestamo, origen, destino, tipo):
        self._sede(origen)
        self._sede(destino)
        remito = Remito(self._id("remitos"), prestamo.id, prestamo.ejemplar_id,
                        origen, destino, tipo)
        remito.notificar("Creación del remito")
        self.remitos.append(remito)
        return remito

    def avanzar_remito(self, remito_id, accion, observacion="", condicion=None):
        remito = self.buscar("remitos", remito_id)
        self._sede(remito.origen_id)
        self._sede(remito.destino_id)
        # Se valida todo antes de avanzar: una acción rechazada no modifica nada.
        if accion == "recibir":
            if condicion is None:
                raise ValueError("Ingrese la condición del ejemplar al recibir el remito.")
            validar_condicion(condicion)
        elif condicion is not None:
            raise ValueError("La condición del ejemplar solo se registra al recibir el remito.")
        ejemplar = self.buscar("ejemplares", remito.ejemplar_id)
        prestamo = self.buscar("prestamos", remito.prestamo_id)
        remito.avanzar(accion, observacion)
        nuevo = remito.estado
        if nuevo == "despachado":
            ejemplar.estado_id = id_estado("Ejemplar", "en_transito")
            ejemplar.ubicacion_id = None
        elif nuevo == "recibido":
            self._recibir(remito, prestamo, ejemplar, condicion)
        elif nuevo == "extraviado":
            # El ejemplar no llegó: su ubicación queda vacía.
            ejemplar.estado_id = id_estado("Ejemplar", "extraviado")
            ejemplar.ubicacion_id = None
            if remito.tipo == "ida":
                prestamo.estado_id = id_estado("Prestamo", "cancelado")
            elif not prestamo.estado.es("cancelado"):
                # El socio ya había devuelto el material.
                prestamo.estado_id = id_estado("Prestamo", "devuelto")
        elif nuevo == "cancelado":
            prestamo.estado_id = id_estado("Prestamo", "cancelado")
            ejemplar.ubicacion_id = ejemplar.sede_id
            self._liberar(ejemplar)

    def _recibir(self, remito, prestamo, ejemplar, condicion):
        remito.condicion_recepcion = condicion
        ejemplar.ubicacion_id = remito.destino_id
        # El traslado puede empeorar la condición del ejemplar, nunca mejorarla.
        if CONDICIONES.index(condicion) > CONDICIONES.index(ejemplar.condicion):
            ejemplar.condicion = condicion
        if remito.tipo == "ida":
            if condicion == "bueno":
                prestamo.estado_id = id_estado("Prestamo", "listo_retiro")
                ejemplar.estado_id = id_estado("Ejemplar", "comprometido")
            else:
                prestamo.estado_id = id_estado("Prestamo", "cancelado")
                ejemplar.estado_id = id_estado("Ejemplar", "fuera_servicio")
                # El ejemplar vuelve a su sede propietaria con el remito de retorno (decisión 19).
                self._crear_remito(prestamo, remito.destino_id, remito.origen_id, "retorno")
        else:
            # Si el préstamo se canceló porque la ida llegó con daño, sigue cancelado.
            if not prestamo.estado.es("cancelado"):
                prestamo.estado_id = id_estado("Prestamo", "devuelto")
            # Si llegó dañado o inutilizable, _liberar() lo deja fuera de servicio.
            self._liberar(ejemplar)

    def devolver(self, prestamo_id, condicion, sede_id=None):
        prestamo = self.buscar("prestamos", prestamo_id)
        # Un préstamo pasa a activo, con su inicio, recién cuando se entrega al socio.
        if not prestamo.estado.es("activo") or prestamo.inicio is None:
            raise ValueError("Debe registrar la entrega al socio antes de devolver el préstamo.")
        self._sede(prestamo.origen_id)
        self._sede(prestamo.destino_id)
        ejemplar = self.buscar("ejemplares", prestamo.ejemplar_id)
        sede_id = prestamo.destino_id if sede_id is None else sede_id
        self._sede(sede_id)
        validar_condicion(condicion)
        fecha = datetime.now()
        if prestamo.inicio > fecha:
            raise ValueError("La devolución no puede preceder a la entrega.")
        ejemplar.ubicacion_id = sede_id
        self.devoluciones.append(Devolucion(self._id("devoluciones"), prestamo.id,
                                           sede_id, fecha, condicion))
        ejemplar.condicion = condicion
        if prestamo.origen_id == sede_id:
            prestamo.estado_id = id_estado("Prestamo", "devuelto")
            self._liberar(ejemplar)
        else:
            ejemplar.estado_id = id_estado("Ejemplar", "comprometido")
            prestamo.estado_id = id_estado("Prestamo", "retornando")
            self._crear_remito(prestamo, sede_id, prestamo.origen_id, "retorno")

    def solicitar(self, socio_id, libro_id, origen_id, destino_id):
        self._socio(socio_id)
        self.buscar("libros", libro_id)
        self._sede(origen_id)
        self._sede(destino_id)
        if any(s.socio_id == socio_id and s.libro_id == libro_id
               and s.estado.es("pendiente")
               for s in self.solicitudes):
            raise ValueError("El socio ya tiene una solicitud pendiente para ese libro.")
        if any(p.socio_id == socio_id and self._abierto(p)
               and self.buscar("ejemplares", p.ejemplar_id).libro_id == libro_id
               for p in self.prestamos):
            raise ValueError("El socio ya tiene una operación de préstamo pendiente para ese libro.")
        solicitud = Solicitud(self._id("solicitudes"), socio_id, libro_id,
                              origen_id, destino_id, datetime.now())
        self.solicitudes.append(solicitud)
        # Decisión 24: si no se puede asignar ahora, el socio queda en la fila de reservas
        # sin cargarla aparte. Si ya tenía esa reserva, conserva su lugar.
        if (not self._puede_asignarse_ya(solicitud)
                and self._reserva_pendiente(socio_id, libro_id, destino_id) is None):
            self.reservar(socio_id, libro_id, destino_id)
        return solicitud

    def _reserva_pendiente(self, socio_id, libro_id, sede_id):
        for reserva in self.reservas:
            if (reserva.socio_id == socio_id and reserva.libro_id == libro_id
                    and reserva.sede_id == sede_id and reserva.estado.es("pendiente")):
                return reserva
        return None

    def _puede_asignarse_ya(self, solicitud):
        """Hay una copia disponible en el origen y ningún otro socio espera ese libro en la sede de retiro."""
        if not self.disponibles(solicitud.libro_id, solicitud.origen_id):
            return False
        return not any(r.libro_id == solicitud.libro_id and r.sede_id == solicitud.destino_id
                       and r.socio_id != solicitud.socio_id and self._en_espera(r)
                       for r in self.reservas)

    def cancelar_solicitud(self, solicitud_id):
        solicitud = self.buscar("solicitudes", solicitud_id)
        if not solicitud.estado.es("pendiente"):
            raise ValueError("La solicitud ya está cerrada.")
        solicitud.estado_id = id_estado("Solicitud", "cancelada")
        # Si el socio ya no quiere el libro, su reserva no debe seguir frenando la fila.
        reserva = self._reserva_pendiente(solicitud.socio_id, solicitud.libro_id, solicitud.destino_id)
        if reserva is not None:
            reserva.cancelar()
        return solicitud

    def asignar_solicitud(self, solicitud_id, ejemplar_id=None):
        solicitud = self.buscar("solicitudes", solicitud_id)
        if not solicitud.estado.es("pendiente"):
            raise ValueError("La solicitud ya está cerrada.")
        candidatos = self.disponibles(solicitud.libro_id, solicitud.origen_id)
        if ejemplar_id is None:
            if not candidatos:
                raise ValueError("No hay ejemplares disponibles en la sede de origen.")
            ejemplar_id = min(candidatos, key=lambda e: e.id).id
        ejemplar = self.buscar("ejemplares", ejemplar_id)
        if ejemplar.libro_id != solicitud.libro_id:
            raise ValueError("El ejemplar no corresponde al libro solicitado.")
        prestamo = self.prestar(solicitud.socio_id, ejemplar_id,
                                solicitud.origen_id, solicitud.destino_id)
        solicitud.estado_id = id_estado("Solicitud", "asignada")
        solicitud.prestamo_id = prestamo.id
        return solicitud

    def iniciar_reparacion(self, ejemplar_id, descripcion):
        ejemplar = self.buscar("ejemplares", ejemplar_id)
        if not ejemplar.estado.es("fuera_servicio"):
            raise ValueError("Solo se repara material fuera de servicio y sin operaciones pendientes.")
        if ejemplar.condicion != "dañado":
            raise ValueError("Solo se repara un ejemplar dañado; uno inutilizable queda fuera de servicio.")
        if any(r.ejemplar_id == ejemplar_id and r.estado not in self.REMITOS_FINALIZADOS
               for r in self.remitos):
            raise ValueError("El ejemplar tiene un remito pendiente; se repara al llegar a su sede.")
        reparacion = Reparacion(self._id("reparaciones"), ejemplar_id,
                                descripcion, datetime.now())
        self.reparaciones.append(reparacion)
        ejemplar.estado_id = id_estado("Ejemplar", "en_reparacion")
        return reparacion

    def finalizar_reparacion(self, reparacion_id, resultado):
        reparacion = self.buscar("reparaciones", reparacion_id)
        if not reparacion.estado.es("abierta"):
            raise ValueError("La reparación ya está cerrada.")
        if resultado not in ("bueno", "inutilizable"):
            raise ValueError("El resultado debe ser bueno o inutilizable.")
        ejemplar = self.buscar("ejemplares", reparacion.ejemplar_id)
        ejemplar.condicion = resultado
        self._liberar(ejemplar)
        reparacion.estado_id = id_estado("Reparacion", "cerrada")
        reparacion.fin = datetime.now()
        reparacion.resultado = resultado
        return reparacion
