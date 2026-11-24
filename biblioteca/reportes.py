"""Strategy: cuatro reportes intercambiables y GeneradorReportes como contexto."""
from abc import ABC, abstractmethod
from datetime import date, datetime


class Reporte(ABC):
    @abstractmethod
    def generar(self, sistema, desde, hasta):
        pass


class PrestamosActivos(Reporte):
    def generar(self, sistema, desde, hasta):
        filas, resumen, por_socio = [], {}, {}
        for p in sistema.prestamos:
            if p.vencimiento is None:
                continue
            devolucion = next((d for d in sistema.devoluciones if d.prestamo_id == p.id), None)
            # La multa corre hasta hoy mientras el socio tiene el material, y hasta la devolución después.
            if p.estado.es("activo"):
                # Los activos son la situación de hoy: figuran siempre, sin filtro de fechas.
                corte = date.today()
            elif devolucion is not None and desde <= devolucion.fecha.date() <= hasta:
                corte = devolucion.fecha
            else:
                continue
            atraso = p.dias_atraso(corte)
            if not p.estado.es("activo") and atraso == 0:
                continue
            multa = p.multa(sistema.MULTA_DIARIA, corte)
            e = sistema.buscar("ejemplares", p.ejemplar_id)
            socio = sistema.buscar("socios", p.socio_id)
            sede = sistema.buscar("sedes", p.destino_id).nombre
            filas.append({"prestamo": p.id, "estado": p.estado.nombre, "socio": socio.nombre,
                          "libro": sistema.buscar("libros", e.libro_id).titulo,
                          "origen": sistema.buscar("sedes", p.origen_id).nombre,
                          "destino": sede, "vencimiento": p.vencimiento.isoformat(),
                          "devolucion": devolucion.fecha.isoformat() if devolucion else None,
                          "dias_atraso": atraso, "multa": multa})
            resumen.setdefault(sede, {"activos": 0, "vencidos": 0, "multas": 0.0})
            if p.estado.es("activo"):
                resumen[sede]["activos"] += 1
                resumen[sede]["vencidos"] += int(atraso > 0)
            resumen[sede]["multas"] += multa
            if multa > 0:
                por_socio.setdefault(socio.id, {"socio": socio.nombre, "prestamos_con_atraso": 0,
                                                "multa_total": 0.0})
                por_socio[socio.id]["prestamos_con_atraso"] += 1
                por_socio[socio.id]["multa_total"] += multa
        multas_por_socio = sorted(por_socio.values(), key=lambda s: (-s["multa_total"], s["socio"]))
        return {"aclaracion": (f"Multa de ${sistema.MULTA_DIARIA:.0f} por día de atraso. Se calcula a hoy para "
                               "los préstamos activos y hasta la devolución para los devueltos con atraso. "
                               "Los activos figuran siempre; el período filtra los devueltos por su "
                               "fecha de devolución. "
                               "Las multas se calculan e informan; el pago no se registra."),
                "detalle": filas, "totales_por_sede": resumen, "multas_por_socio": multas_por_socio}


class Disponibilidad(Reporte):
    def generar(self, sistema, desde, hasta):
        filas = []
        for sede in sistema.sedes:
            for libro in sistema.libros:
                propios = [e for e in sistema.ejemplares
                           if e.sede_id == sede.id and e.libro_id == libro.id]
                presentes = [e for e in sistema.ejemplares
                            if e.ubicacion_id == sede.id and e.libro_id == libro.id]
                if not propios and not presentes:
                    continue
                filas.append({"sede": sede.nombre, "libro": libro.titulo,
                              "propios": len(propios), "presentes": len(presentes),
                              "disponibles_para_prestar": sum(e.estado.es("disponible")
                                  and e.condicion == "bueno" and e.ubicacion_id == sede.id
                                  and sede.activa for e in propios),
                              "propios_comprometidos": sum(e.estado.es("comprometido") for e in propios),
                              "propios_prestados": sum(e.estado.es("prestado") for e in propios),
                              "propios_en_reparacion": sum(e.estado.es("en_reparacion") for e in propios),
                              "propios_disponibles": sum(e.estado.es("disponible") for e in propios),
                              "propios_en_transito": sum(e.estado.es("en_transito") for e in propios),
                              "propios_fuera_servicio": sum(e.estado.es("fuera_servicio") for e in propios),
                              "propios_extraviados": sum(e.estado.es("extraviado") for e in propios)})
        return {"aclaracion": "Fotografía actual; no utiliza el filtro de fechas. Propios y ubicación registrada son perspectivas distintas: no se suman. Ubicación registrada incluye material entregado al socio. Los estados propios son categorías excluyentes.", "detalle": filas}


class MasSolicitados(Reporte):
    def generar(self, sistema, desde, hasta):
        # Ranking de préstamos interbibliotecarios del período; los cancelados no cuentan.
        cantidades = {}
        for p in sistema.prestamos:
            if (p.origen_id != p.destino_id and not p.estado.es("cancelado")
                    and desde <= p.fecha_solicitud <= hasta):
                libro_id = sistema.buscar("ejemplares", p.ejemplar_id).libro_id
                cantidades[libro_id] = cantidades.get(libro_id, 0) + 1
        total = sum(cantidades.values())
        return [{"libro_id": libro_id, "libro": sistema.buscar("libros", libro_id).titulo,
                 "prestamos": cantidad, "porcentaje": round(cantidad * 100 / total, 2)}
                for libro_id, cantidad in sorted(cantidades.items(), key=lambda x: (-x[1], x[0]))]


class Movimientos(Reporte):
    def generar(self, sistema, desde, hasta):
        grupos = {}
        for r in sistema.remitos:
            historial = r.consultar_historial()
            if not historial or not desde <= date.fromisoformat(historial[0]["fecha"][:10]) <= hasta:
                continue
            clave = (r.origen_id, r.destino_id)
            if clave not in grupos:
                grupos[clave] = {"origen": sistema.buscar("sedes", r.origen_id).nombre,
                                 "destino": sistema.buscar("sedes", r.destino_id).nombre,
                                 "envios": 0, "pendientes": 0, "en_transito": 0,
                                 "recibidos_sin_novedad": 0, "recibidos_con_danio": 0,
                                 "extraviados": 0, "cancelados": 0, "segundos": []}
            fila = grupos[clave]
            fila["envios"] += 1
            if r.estado == "recibido":
                if r.condicion_recepcion == "bueno":
                    fila["recibidos_sin_novedad"] += 1
                else:
                    fila["recibidos_con_danio"] += 1
                fechas = {h["estado"]: datetime.fromisoformat(h["fecha"]) for h in r.consultar_historial()}
                fila["segundos"].append((fechas["recibido"] - fechas["despachado"]).total_seconds())
            elif r.estado == "extraviado":
                fila["extraviados"] += 1
            elif r.estado == "cancelado":
                fila["cancelados"] += 1
            elif r.estado == "despachado":
                fila["en_transito"] += 1
            else:
                fila["pendientes"] += 1
        for fila in grupos.values():
            # Tasa = recibidos sin novedad / (recibidos + extraviados) (decisión del grupo).
            recibidos = fila["recibidos_sin_novedad"] + fila["recibidos_con_danio"]
            finalizados = recibidos + fila["extraviados"]
            fila["tasa_envios_exitosos"] = (round(fila["recibidos_sin_novedad"] * 100 / finalizados, 2)
                                            if finalizados else None)
            segundos = fila.pop("segundos")
            fila["promedio_segundos_transito"] = sum(segundos) / len(segundos) if segundos else None
        return list(grupos.values())


class GeneradorReportes:
    """Contexto: valida el período y delega el cálculo en la estrategia elegida."""

    def __init__(self, reporte=None):
        self.reporte = None
        if reporte is not None:
            self.establecer_reporte(reporte)

    def establecer_reporte(self, reporte):
        if not isinstance(reporte, Reporte):
            raise ValueError("Elija un reporte válido.")
        self.reporte = reporte

    def generar(self, sistema, desde="0001-01-01", hasta="9999-12-31"):
        if self.reporte is None:
            raise ValueError("Elija un reporte antes de generarlo.")
        desde = date.fromisoformat(desde)
        hasta = date.fromisoformat(hasta)
        if desde > hasta:
            raise ValueError("La fecha inicial no puede superar a la final.")
        return self.reporte.generar(sistema, desde, hasta)
