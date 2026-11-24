"""API JSON y frontend del TP. Una transacción por operación de escritura."""
import secrets
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from werkzeug.exceptions import HTTPException

from .validaciones import armar_horarios
from .orm import db, FILAS, cargar_dominio, guardar_dominio, serializar, cargar_estados
from .reportes import (GeneradorReportes, PrestamosActivos,
                       Disponibilidad, MasSolicitados, Movimientos)
from .reportes_pdf import armar_pdf, nombre_archivo
from . import usuarios
from .orm import UsuarioFila

# Lo único que se puede pedir sin haber iniciado sesión (decisión 28).
SIN_SESION = {("GET", "/api/sesion"), ("POST", "/api/login"), ("POST", "/api/usuarios/primero")}


def clave_secreta(ruta_base):
    """La clave que firma la sesión se guarda junto a la base, así sobrevive a un reinicio."""
    if ruta_base == ":memory:":
        return secrets.token_hex(32)
    archivo = Path(ruta_base).resolve().parent / "clave_secreta"
    if not archivo.exists():
        archivo.write_text(secrets.token_hex(32))
    return archivo.read_text().strip()

RAIZ = Path(__file__).resolve().parent.parent
REPORTES = {"prestamos": PrestamosActivos, "disponibilidad": Disponibilidad,
            "solicitados": MasSolicitados, "movimientos": Movimientos}


def datos_json(obligatorios=(), opcionales=()):
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ValueError("Ingrese un objeto JSON válido.")
    if set(datos) - set(obligatorios) - set(opcionales):
        raise ValueError("La operación contiene campos no permitidos.")
    if set(obligatorios) - set(datos):
        raise ValueError("Faltan campos obligatorios: " + ", ".join(sorted(set(obligatorios) - set(datos))))
    for campo, valor in datos.items():
        if campo.endswith("_id"):
            if campo == "ejemplar_id" and valor is None and campo in opcionales:
                continue
            if type(valor) is not int or valor <= 0:
                raise ValueError("Los identificadores deben ser enteros positivos.")
        elif campo in ("activa", "habilitado"):
            if type(valor) is not bool:
                raise ValueError("El estado debe ser verdadero o falso.")
        elif not isinstance(valor, str):
            raise ValueError("El campo " + campo + " debe ser texto.")
    return datos


def preparar_horarios(datos, requerido=False):
    campos = {"dias", "apertura", "cierre"}
    if campos & set(datos):
        if not campos <= set(datos) or "horarios" in datos:
            raise ValueError("Ingrese días, apertura y cierre juntos, sin un horario de texto adicional.")
        datos["horarios"] = armar_horarios(*(datos.pop(c) for c in ("dias", "apertura", "cierre")))
    if requerido and "horarios" not in datos:
        raise ValueError("Ingrese los días y horarios de atención.")


def modificar(operacion, coleccion, codigo=200):
    # BEGIN IMMEDIATE serializa asignaciones y evita prestar dos veces la misma copia.
    db.session.execute(text("BEGIN IMMEDIATE"))
    sistema = cargar_dominio()
    objeto = operacion(sistema)
    guardar_dominio(sistema)
    respuesta = serializar(objeto, coleccion, sistema)
    db.session.commit()
    return jsonify(respuesta), codigo


def crear_app(configuracion=None):
    app = Flask(__name__, template_folder=str(RAIZ / "templates"),
                static_folder=str(RAIZ / "static"))
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///" + str(RAIZ / "instance/biblioteca_web.db"),
                      SQLALCHEMY_TRACK_MODIFICATIONS=False, MAX_CONTENT_LENGTH=64 * 1024)
    if configuracion:
        app.config.update(configuracion)
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        raise ValueError("Este TP utiliza SQLite.")
    ruta = uri.removeprefix("sqlite:///")
    if ruta != ":memory:":
        Path(ruta).resolve().parent.mkdir(parents=True, exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = clave_secreta(ruta)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    db.init_app(app)
    with app.app_context():
        db.create_all()
        cargar_estados()

    @app.before_request
    def exigir_sesion():
        # El control está en el servidor: aunque se saltee la pantalla, la API pide sesión.
        if not request.path.startswith("/api/") or (request.method, request.path) in SIN_SESION:
            return None
        fila = db.session.get(UsuarioFila, session["usuario_id"]) if "usuario_id" in session else None
        if fila is None or not fila.activo:
            session.clear()
            return jsonify(error="Inicie sesión para usar el sistema."), 401
        return None

    @app.before_request
    def iniciar_lectura():
        if request.method == "GET" and request.path.startswith("/api/"):
            db.session.execute(text("BEGIN"))

    @app.teardown_request
    def cerrar_transaccion(error):
        # También cierra lecturas si el cliente conserva un contexto de aplicación.
        # Las escrituras correctas ya hicieron commit en modificar().
        db.session.rollback()

    @app.errorhandler(ValueError)
    def error_validacion(error):
        db.session.rollback()
        return jsonify(error=str(error)), 400

    @app.errorhandler(IntegrityError)
    def error_integridad(error):
        db.session.rollback()
        return jsonify(error="La operación viola una relación o duplica un registro. No se guardaron cambios."), 409

    @app.errorhandler(OperationalError)
    def error_operacion(error):
        db.session.rollback()
        app.logger.error("Error SQLite: %s", error)
        return jsonify(error="No se pudo guardar o consultar la base. Intente nuevamente."), 503

    @app.errorhandler(HTTPException)
    def error_http(error):
        db.session.rollback()
        return jsonify(error=error.description), error.code

    @app.get("/")
    def inicio():
        return render_template("index.html")

    # --- Sesión y cuentas del personal (decisión 28) ---

    @app.get("/api/sesion")
    def ver_sesion():
        fila = db.session.get(UsuarioFila, session["usuario_id"]) if "usuario_id" in session else None
        if fila is None or not fila.activo:
            return jsonify(usuario=None, sin_usuarios=not usuarios.hay_usuarios())
        return jsonify(usuarios.a_json(fila))

    def abrir_sesion(fila):
        session.clear()
        session["usuario_id"] = fila.id

    @app.post("/api/login")
    def login():
        datos = datos_json(("usuario", "clave"))
        fila = usuarios.autenticar(datos["usuario"], datos["clave"])
        if fila is None:
            # Mismo mensaje si no existe el usuario o si falla la contraseña.
            return jsonify(error="Usuario o contraseña incorrectos."), 401
        abrir_sesion(fila)
        return jsonify(usuarios.a_json(fila))

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.post("/api/usuarios/primero")
    def crear_primer_usuario():
        # Solo sirve con la base sin cuentas: así se crea el primer usuario sin usar la terminal.
        datos = datos_json(("usuario", "nombre", "clave"))
        db.session.execute(text("BEGIN IMMEDIATE"))
        if usuarios.hay_usuarios():
            return jsonify(error="Ya hay usuarios: inicie sesión."), 403
        fila = usuarios.crear(**datos)
        db.session.commit()
        abrir_sesion(fila)
        return jsonify(usuarios.a_json(fila)), 201

    @app.get("/api/usuarios")
    def listar_usuarios():
        return jsonify([usuarios.a_json(f) for f in usuarios.listar()])

    @app.post("/api/usuarios")
    def alta_usuario():
        datos = datos_json(("usuario", "nombre", "clave"))
        fila = usuarios.crear(**datos)
        db.session.commit()
        return jsonify(usuarios.a_json(fila)), 201

    @app.post("/api/usuarios/<int:identificador>/<accion>")
    def activar_usuario(identificador, accion):
        if accion not in ("activar", "desactivar"):
            return jsonify(error="Acción inexistente."), 404
        fila = usuarios.cambiar_activo(identificador, accion == "activar", session["usuario_id"])
        db.session.commit()
        return jsonify(usuarios.a_json(fila))

    @app.get("/api/estado")
    def estado():
        sistema = cargar_dominio()
        return jsonify({n: [serializar(o, n, sistema) for o in objetos]
                        for n, objetos in sistema.colecciones().items()})

    @app.get("/api/<coleccion>")
    def listar(coleccion):
        if coleccion not in FILAS:
            return jsonify(error="Colección inexistente."), 404
        sistema = cargar_dominio()
        return jsonify([serializar(o, coleccion, sistema) for o in sistema.colecciones()[coleccion]])

    @app.get("/api/<coleccion>/<int:identificador>")
    def detalle(coleccion, identificador):
        if coleccion not in FILAS or db.session.get(FILAS[coleccion], identificador) is None:
            return jsonify(error="Registro inexistente."), 404
        sistema = cargar_dominio()
        return jsonify(serializar(sistema.buscar(coleccion, identificador), coleccion, sistema))

    @app.post("/api/<coleccion>")
    def alta(coleccion):
        campos = {"sedes": ("nombre", "direccion", "contacto", "horarios"),
                  "socios": ("dni", "nombre", "contacto"),
                  "libros": ("isbn", "titulo", "autor"),
                  "ejemplares": ("codigo", "libro_id", "sede_id"),
                  "solicitudes": ("socio_id", "libro_id", "origen_id", "destino_id"),
                  "prestamos": ("socio_id", "ejemplar_id", "origen_id", "destino_id"),
                  "reservas": ("socio_id", "libro_id", "sede_id"),
                  "devoluciones": ("prestamo_id", "condicion", "sede_id"),
                  "reparaciones": ("ejemplar_id", "descripcion")}
        if coleccion not in campos:
            return jsonify(error="Alta no permitida. Los remitos se generan desde el préstamo o la devolución."), 405
        if coleccion == "sedes":
            datos = datos_json(("nombre", "direccion", "contacto"), ("horarios", "dias", "apertura", "cierre"))
            preparar_horarios(datos, requerido=True)
        else:
            datos = datos_json(campos[coleccion])

        def operar(sistema):
            if coleccion == "prestamos":
                ejemplar = sistema.buscar("ejemplares", datos["ejemplar_id"])
                solicitud = sistema.solicitar(datos["socio_id"], ejemplar.libro_id,
                                               datos["origen_id"], datos["destino_id"])
                sistema.asignar_solicitud(solicitud.id, ejemplar.id)
                return sistema.buscar("prestamos", solicitud.prestamo_id)
            if coleccion == "devoluciones":
                sistema.devolver(**datos)
                return sistema.devoluciones[-1]
            operaciones = {"sedes": sistema.agregar_sede, "socios": sistema.agregar_socio,
                           "libros": sistema.agregar_libro, "ejemplares": sistema.agregar_ejemplar,
                           "solicitudes": sistema.solicitar, "reservas": sistema.reservar,
                           "reparaciones": sistema.iniciar_reparacion}
            return operaciones[coleccion](**datos)
        return modificar(operar, coleccion, 201)

    @app.patch("/api/<coleccion>/<int:identificador>")
    def editar(coleccion, identificador):
        campos = {"sedes": ("nombre", "direccion", "contacto", "horarios", "activa", "dias", "apertura", "cierre"),
                  "socios": ("nombre", "contacto", "habilitado"),
                  "libros": ("titulo", "autor"), "ejemplares": ("condicion",)}
        if coleccion not in campos:
            return jsonify(error="Edición no permitida."), 405
        datos = datos_json(opcionales=campos[coleccion])
        if coleccion == "sedes":
            preparar_horarios(datos)
        if not datos:
            raise ValueError("Ingrese al menos un cambio.")

        def operar(sistema):
            cambios = datos.copy()
            if "activa" in cambios:
                sistema.cambiar_sede(identificador, cambios.pop("activa"))
            if "habilitado" in cambios:
                sistema.cambiar_socio(identificador, cambios.pop("habilitado"))
            if coleccion == "ejemplares":
                sistema.cambiar_condicion(identificador, cambios.pop("condicion"))
            elif cambios:
                sistema.editar(coleccion, identificador, **cambios)
            return sistema.buscar(coleccion, identificador)
        return modificar(operar, coleccion)

    @app.post("/api/prestamos/<int:identificador>/entregar")
    def entregar(identificador):
        datos_json()
        return modificar(lambda s: s.entregar(identificador), "prestamos")

    @app.post("/api/solicitudes/<int:identificador>/asignar")
    def asignar(identificador):
        datos = datos_json(opcionales=("ejemplar_id",))
        return modificar(lambda s: s.asignar_solicitud(identificador, **datos), "solicitudes")

    @app.post("/api/<coleccion>/<int:identificador>/cancelar")
    def cancelar(coleccion, identificador):
        datos_json()
        if coleccion not in ("solicitudes", "reservas"):
            return jsonify(error="Cancelación no permitida."), 405

        def operar(sistema):
            if coleccion == "solicitudes":
                sistema.cancelar_solicitud(identificador)
            else:
                sistema.cancelar_reserva(identificador)
            return sistema.buscar(coleccion, identificador)
        return modificar(operar, coleccion)

    @app.post("/api/remitos/<int:identificador>/avanzar")
    def avanzar(identificador):
        datos = datos_json(("accion",), ("observacion", "condicion"))

        def operar(sistema):
            sistema.avanzar_remito(identificador, **datos)
            return sistema.buscar("remitos", identificador)
        return modificar(operar, "remitos")

    @app.post("/api/reparaciones/<int:identificador>/finalizar")
    def reparar(identificador):
        datos = datos_json(("resultado",))
        return modificar(lambda s: s.finalizar_reparacion(identificador, **datos), "reparaciones")

    @app.get("/api/disponibilidad")
    def disponibilidad():
        try:
            libro_id = int(request.args["libro_id"])
            sede_id = int(request.args["sede_id"])
        except (KeyError, ValueError):
            raise ValueError("Ingrese libro_id y sede_id como enteros positivos.") from None
        if libro_id <= 0 or sede_id <= 0:
            raise ValueError("Los identificadores deben ser positivos.")
        modo = request.args.get("modo", "disponibles")
        if modo not in ("disponibles", "todos"):
            raise ValueError("El modo de consulta debe ser disponibles o todos.")
        sistema = cargar_dominio()
        resultados = sistema.consultar_ejemplares(libro_id, sede_id)
        filas = []
        for ejemplar, disponible, motivo in resultados:
            if modo == "todos" or disponible:
                filas.append({**serializar(ejemplar, "ejemplares", sistema),
                              "disponible": disponible, "motivo": motivo})
        return jsonify(filas)

    @app.get("/api/reportes/<tipo>")
    def reporte(tipo):
        if tipo not in REPORTES:
            return jsonify(error="Reporte inexistente."), 404
        generador = GeneradorReportes()
        generador.establecer_reporte(REPORTES[tipo]())
        datos = generador.generar(cargar_dominio(), request.args.get("desde") or "0001-01-01",
                                  request.args.get("hasta") or "9999-12-31")
        return jsonify(datos)

    @app.get("/api/reportes/<tipo>/pdf")
    def reporte_pdf(tipo):
        # Misma estrategia que la ruta anterior; solo cambia la presentación del resultado.
        if tipo not in REPORTES:
            return jsonify(error="Reporte inexistente."), 404
        desde = request.args.get("desde") or None
        hasta = request.args.get("hasta") or None
        generador = GeneradorReportes()
        generador.establecer_reporte(REPORTES[tipo]())
        datos = generador.generar(cargar_dominio(), desde or "0001-01-01", hasta or "9999-12-31")
        return Response(armar_pdf(tipo, datos, desde, hasta), mimetype="application/pdf",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{nombre_archivo(tipo)}"'})

    return app
