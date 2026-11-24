"""Remito: estados Extraviado y Cancelado, condición de recepción e incidencias (Vista 2 y State)."""
import pytest

from biblioteca.estados_remito import (Empaquetado, Despachado, Recibido,
                                       Extraviado, Cancelado)
from biblioteca.modelos import Remito
from biblioteca.observadores import ObservadorRemito
from biblioteca.orm import db, guardar_dominio, cargar_dominio
from biblioteca.sistema import Biblioteca
from biblioteca.web import crear_app
from sesion import iniciar_sesion


class ObservadorPrueba(ObservadorRemito):
    def __init__(self):
        self.eventos = []

    def actualizar(self, remito, observacion):
        self.eventos.append(remito.estado)


ACCIONES = ["empaquetar", "despachar", "recibir", "informar_extravio", "cancelar", "desconocida"]

# Transiciones del diagrama de State del documento entregado.
TRANSICIONES = {
    "pendiente": {"empaquetar": Empaquetado, "cancelar": Cancelado},
    "empaquetado": {"despachar": Despachado, "cancelar": Cancelado},
    "despachado": {"recibir": Recibido, "informar_extravio": Extraviado},
    "recibido": {},
    "extraviado": {},
    "cancelado": {},
}


@pytest.mark.parametrize("estado, accion, siguiente",
                         [(e, a, s) for e, t in TRANSICIONES.items() for a, s in t.items()])
def test_transiciones_validas_notifican_una_vez(estado, accion, siguiente):
    remito = Remito(1, 1, 1, 1, 2, "ida", estado)
    observador = ObservadorPrueba()
    remito.suscribir(observador)
    remito.avanzar(accion, "Control")
    assert isinstance(remito._estado, siguiente)
    assert observador.eventos == [siguiente.nombre]
    assert remito.consultar_historial()[-1]["estado"] == siguiente.nombre


@pytest.mark.parametrize("estado, accion",
                         [(e, a) for e, t in TRANSICIONES.items() for a in ACCIONES if a not in t])
def test_transiciones_invalidas_no_modifican_ni_notifican(estado, accion):
    remito = Remito(1, 1, 1, 1, 2, "ida", estado)
    observador = ObservadorPrueba()
    remito.suscribir(observador)
    anterior = remito._estado
    with pytest.raises(ValueError):
        remito.avanzar(accion)
    assert remito._estado is anterior
    assert observador.eventos == []
    assert remito.consultar_historial() == []


@pytest.mark.parametrize("estado", ["pendiente", "empaquetado"])
def test_remito_de_retorno_no_se_cancela(estado):
    remito = Remito(1, 1, 1, 2, 1, "retorno", estado)
    observador = ObservadorPrueba()
    remito.suscribir(observador)
    with pytest.raises(ValueError):
        remito.avanzar("cancelar")
    assert remito.estado == estado
    assert observador.eventos == []


def test_estados_finales_y_condicion_invalida():
    for tipo in (Recibido, Extraviado, Cancelado):
        assert Remito(1, 1, 1, 1, 2, "ida", tipo.nombre).estado == tipo.nombre
    with pytest.raises(ValueError):
        Remito(1, 1, 1, 1, 2, "ida", "recibido", "roto")


# --- Efectos sobre el préstamo y el ejemplar (tabla de incidencias) ---

def crear_biblioteca():
    b = Biblioteca()
    b.agregar_sede("Centro", "Calle 1", "111", "8 a 18")
    b.agregar_sede("Norte", "Calle 2", "222", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_libro("978-1", "El principito", "Saint-Exupéry")
    b.agregar_ejemplar("E1", 1, 1)
    b.prestar(1, 1, 1, 2)
    return b


def despachar(b, remito_id):
    b.avanzar_remito(remito_id, "empaquetar")
    b.avanzar_remito(remito_id, "despachar")


def con_retorno(condicion_devolucion="bueno"):
    """Préstamo entregado en Norte y devuelto allí: genera el remito 2 hacia Centro."""
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion="bueno")
    b.entregar(1)
    b.devolver(1, condicion_devolucion)
    despachar(b, 2)
    return b


def test_recibir_ida_en_buen_estado():
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion="bueno")
    p, e, r = b.prestamos[0], b.ejemplares[0], b.remitos[0]
    assert p.estado.es("listo_retiro")
    assert e.estado.es("comprometido") and e.ubicacion_id == 2 and e.condicion == "bueno"
    assert r.condicion_recepcion == "bueno"


@pytest.mark.parametrize("condicion", ["dañado", "inutilizable"])
def test_recibir_ida_danado_cancela_el_prestamo(condicion):
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion=condicion)
    p, e = b.prestamos[0], b.ejemplares[0]
    assert p.estado.es("cancelado")
    assert e.estado.es("fuera_servicio") and e.ubicacion_id == 2 and e.condicion == condicion
    assert b.remitos[0].condicion_recepcion == condicion
    with pytest.raises(ValueError):
        b.entregar(1)


# --- Ida recibida con daño: el ejemplar vuelve a su sede propietaria (decisión 19) ---

def ida_con_danio(condicion="dañado"):
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion=condicion)
    return b


def test_ida_danada_crea_el_remito_de_retorno():
    b = ida_con_danio()
    retorno = b.remitos[1]
    assert len(b.remitos) == 2
    assert (retorno.prestamo_id, retorno.tipo, retorno.estado) == (1, "retorno", "pendiente")
    assert (retorno.origen_id, retorno.destino_id) == (2, 1)
    # Un retorno no se cancela y el ejemplar no se repara hasta que llegue.
    with pytest.raises(ValueError):
        b.avanzar_remito(2, "cancelar")
    with pytest.raises(ValueError, match="remito pendiente"):
        b.iniciar_reparacion(1, "Lomo despegado")


def test_ida_danada_vuelve_se_repara_y_circula_de_nuevo():
    b = ida_con_danio()
    despachar(b, 2)
    assert b.ejemplares[0].estado.es("en_transito")
    b.avanzar_remito(2, "recibir", condicion="dañado")
    p, e = b.prestamos[0], b.ejemplares[0]
    # El préstamo nunca se entregó: sigue cancelado, no pasa a devuelto.
    assert p.estado.es("cancelado")
    assert e.estado.es("fuera_servicio") and e.ubicacion_id == 1 and e.condicion == "dañado"
    reparacion = b.iniciar_reparacion(1, "Lomo despegado")
    b.finalizar_reparacion(reparacion.id, "bueno")
    assert len(b.disponibles(1, 1)) == 1
    b.prestar(1, 1, 1, 2)


def test_ida_inutilizable_vuelve_y_queda_fuera_de_servicio():
    b = ida_con_danio("inutilizable")
    despachar(b, 2)
    b.avanzar_remito(2, "recibir", condicion="inutilizable")
    e = b.ejemplares[0]
    assert e.estado.es("fuera_servicio") and e.ubicacion_id == 1
    assert b.prestamos[0].estado.es("cancelado")


def test_ida_danada_con_retorno_extraviado():
    b = ida_con_danio()
    despachar(b, 2)
    b.avanzar_remito(2, "informar_extravio")
    e = b.ejemplares[0]
    assert e.estado.es("extraviado") and e.ubicacion_id is None
    assert b.prestamos[0].estado.es("cancelado")


def test_recibir_retorno_en_buen_estado():
    b = con_retorno()
    b.avanzar_remito(2, "recibir", condicion="bueno")
    p, e = b.prestamos[0], b.ejemplares[0]
    assert p.estado.es("devuelto")
    assert e.estado.es("disponible") and e.ubicacion_id == 1
    assert len(b.disponibles(1, 1)) == 1


@pytest.mark.parametrize("condicion", ["dañado", "inutilizable"])
def test_recibir_retorno_danado(condicion):
    b = con_retorno()
    b.avanzar_remito(2, "recibir", condicion=condicion)
    p, e = b.prestamos[0], b.ejemplares[0]
    assert p.estado.es("devuelto")
    assert e.estado.es("fuera_servicio") and e.ubicacion_id == 1 and e.condicion == condicion
    assert b.remitos[1].condicion_recepcion == condicion


def test_recibir_retorno_bueno_no_repara_material_devuelto_danado():
    b = con_retorno("dañado")
    b.avanzar_remito(2, "recibir", condicion="bueno")
    e = b.ejemplares[0]
    assert e.condicion == "dañado" and e.estado.es("fuera_servicio")


def test_recibir_retorno_danado_no_mejora_material_devuelto_inutilizable():
    b = con_retorno("inutilizable")
    b.avanzar_remito(2, "recibir", condicion="dañado")
    ejemplar = b.ejemplares[0]
    assert ejemplar.condicion == "inutilizable" and ejemplar.estado.es("fuera_servicio")
    assert b.remitos[1].condicion_recepcion == "dañado"


def test_extravio_de_ida():
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "informar_extravio", "No llegó a destino")
    p, e = b.prestamos[0], b.ejemplares[0]
    assert b.remitos[0].estado == "extraviado"
    assert p.estado.es("cancelado")
    assert e.estado.es("extraviado") and e.ubicacion_id is None
    assert b.remitos[0].condicion_recepcion is None


def test_extravio_de_retorno():
    b = con_retorno()
    b.avanzar_remito(2, "informar_extravio")
    p, e = b.prestamos[0], b.ejemplares[0]
    assert p.estado.es("devuelto")
    assert e.estado.es("extraviado") and e.ubicacion_id is None


@pytest.mark.parametrize("acciones_previas", [[], ["empaquetar"]])
def test_cancelar_ida_antes_del_despacho(acciones_previas):
    b = crear_biblioteca()
    for accion in acciones_previas:
        b.avanzar_remito(1, accion)
    b.avanzar_remito(1, "cancelar", "El socio desistió")
    p, e = b.prestamos[0], b.ejemplares[0]
    assert b.remitos[0].estado == "cancelado"
    assert p.estado.es("cancelado")
    assert e.estado.es("disponible") and e.ubicacion_id == e.sede_id == 1
    assert len(b.disponibles(1, 1)) == 1


def test_cancelar_retorno_no_permitido_y_no_modifica():
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion="bueno")
    b.entregar(1)
    b.devolver(1, "bueno")
    historial = b.remitos[1].consultar_historial()
    with pytest.raises(ValueError):
        b.avanzar_remito(2, "cancelar")
    assert b.remitos[1].estado == "pendiente"
    assert b.remitos[1].consultar_historial() == historial
    assert b.prestamos[0].estado.es("retornando")
    assert b.ejemplares[0].estado.es("comprometido")


def test_no_se_cancela_despues_del_despacho():
    b = crear_biblioteca()
    despachar(b, 1)
    with pytest.raises(ValueError):
        b.avanzar_remito(1, "cancelar")
    assert b.prestamos[0].estado.es("esperando_envio")
    assert b.ejemplares[0].estado.es("en_transito")


def test_condicion_obligatoria_solo_al_recibir():
    b = crear_biblioteca()
    with pytest.raises(ValueError):
        b.avanzar_remito(1, "empaquetar", condicion="bueno")
    despachar(b, 1)
    for condicion in (None, "roto"):
        with pytest.raises(ValueError):
            b.avanzar_remito(1, "recibir", condicion=condicion)
    assert b.remitos[0].estado == "despachado"
    assert b.remitos[0].condicion_recepcion is None
    assert len(b.remitos[0].consultar_historial()) == 3
    assert b.ejemplares[0].ubicacion_id is None


def test_prestamo_cancelado_queda_cerrado():
    b = crear_biblioteca()
    b.avanzar_remito(1, "cancelar")
    # Ya no bloquea un nuevo préstamo del mismo libro ni la baja de la sede.
    b.prestar(1, 1, 1, 1)
    b.entregar(2)
    b.devolver(2, "bueno")
    b.cambiar_sede(2, False)
    assert not b.sedes[1].activa


def test_disponibilidad_informa_extraviado():
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "informar_extravio")
    b.ejemplares[0].ubicacion_id = 1  # Solo para que la consulta lo encuentre en la sede.
    _, disponible, motivo = b.consultar_ejemplares(1, 1)[0]
    assert not disponible and "extraviado" in motivo
    assert "tránsito" not in motivo


# --- Persistencia y API ---

def test_persistencia_de_incidencias(recargar):
    b = crear_biblioteca()
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion="dañado")
    copia = recargar(b)
    assert copia.remitos[0].estado == "recibido"
    assert copia.remitos[0].condicion_recepcion == "dañado"
    assert copia.prestamos[0].estado.es("cancelado")


def test_orm_y_api_de_extravio_y_cancelacion(tmp_path):
    app = crear_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "web.db")})
    cliente = iniciar_sesion(app.test_client())
    with app.app_context():
        b = crear_biblioteca()
        b.agregar_ejemplar("E2", 1, 1)
        b.agregar_socio("456", "Luis", "luis@mail")
        b.prestar(2, 2, 1, 2)
        guardar_dominio(b)
        db.session.commit()

    def avanzar(remito_id, esperado, **datos):
        respuesta = cliente.post(f"/api/remitos/{remito_id}/avanzar", json=datos)
        assert respuesta.status_code == esperado, respuesta.json
        return respuesta.json

    avanzar(1, 400, accion="empaquetar", condicion="bueno")
    avanzar(1, 200, accion="empaquetar")
    avanzar(1, 200, accion="despachar")
    avanzar(1, 400, accion="recibir")
    remito = avanzar(1, 200, accion="informar_extravio", observacion="No llegó")
    assert remito["estado"] == "extraviado"
    assert [h["estado"] for h in remito["historial"]] == ["pendiente", "empaquetado", "despachado", "extraviado"]
    assert avanzar(2, 200, accion="cancelar")["estado"] == "cancelado"
    estado = cliente.get("/api/estado").json
    assert [p["estado"] for p in estado["prestamos"]] == ["cancelado", "cancelado"]
    assert [e["estado"] for e in estado["ejemplares"]] == ["extraviado", "disponible"]
    with app.app_context():
        copia = cargar_dominio()
        assert [r.estado for r in copia.remitos] == ["extraviado", "cancelado"]
        db.session.remove()
        db.engine.dispose()


def test_api_recibe_con_condicion(tmp_path):
    app = crear_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "web.db")})
    cliente = iniciar_sesion(app.test_client())
    with app.app_context():
        b = crear_biblioteca()
        despachar(b, 1)
        guardar_dominio(b)
        db.session.commit()
    respuesta = cliente.post("/api/remitos/1/avanzar", json={"accion": "recibir", "condicion": "inutilizable"})
    assert respuesta.status_code == 200
    assert respuesta.json["condicion_recepcion"] == "inutilizable"
    assert cliente.get("/api/prestamos").json[0]["estado"] == "cancelado"
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


# --- Reservas cuando el préstamo no llega al socio ---

def biblioteca_con_reservas():
    b = Biblioteca()
    for nombre in ("Centro", "Norte"):
        b.agregar_sede(nombre, "Calle 1", "111", "8 a 18")
    b.agregar_socio("123", "Ana", "ana@mail")
    b.agregar_socio("456", "Luis", "luis@mail")
    b.agregar_libro("978-1", "El principito", "Saint-Exupéry")
    b.agregar_ejemplar("E1", 1, 1)
    b.agregar_ejemplar("E2", 1, 1)
    b.reservar(1, 1, 2)      # Ana, primera en la cola de Norte.
    b.reservar(2, 1, 2)      # Luis, segundo.
    b.prestar(1, 1, 1, 2)
    return b


@pytest.mark.parametrize("incidencia", ["cancelar", "extravio", "dañado"])
def test_reserva_conserva_su_lugar_si_el_prestamo_se_cancela(incidencia):
    b = biblioteca_con_reservas()
    if incidencia == "cancelar":
        b.avanzar_remito(1, "cancelar")
    else:
        despachar(b, 1)
        if incidencia == "extravio":
            b.avanzar_remito(1, "informar_extravio")
        else:
            b.avanzar_remito(1, "recibir", condicion="dañado")
    assert b.prestamos[0].estado.es("cancelado")
    assert [r.estado.nombre for r in b.reservas] == ["pendiente", "pendiente"]
    # Ana sigue primera: Luis no puede adelantarse y ella vuelve a pedir el libro.
    with pytest.raises(ValueError, match="prioridad"):
        b.prestar(2, 2, 1, 2)
    b.prestar(1, 2, 1, 2)


def test_reserva_se_atiende_al_entregar_y_no_frena_al_siguiente():
    b = biblioteca_con_reservas()
    # Ana ya tiene su préstamo en curso: Luis, que sigue en la cola, puede pedir otra copia.
    b.prestar(2, 2, 1, 2)
    despachar(b, 1)
    b.avanzar_remito(1, "recibir", condicion="bueno")
    assert b.reservas[0].estado.es("pendiente")
    b.entregar(1)
    assert [r.estado.nombre for r in b.reservas] == ["atendida", "pendiente"]
