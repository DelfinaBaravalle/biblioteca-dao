"""Exporta a PDF el resultado de un reporte.

No calcula nada: recibe lo que devolvió la estrategia elegida en GeneradorReportes
y lo presenta en tablas. Así la pantalla y el PDF muestran el mismo cálculo.
"""
from datetime import date, datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

TITULOS = {"prestamos": "Préstamos activos, vencidos y multas",
           "disponibilidad": "Disponibilidad del catálogo por sede",
           "solicitados": "Libros más solicitados entre sedes",
           "movimientos": "Movimientos logísticos e incidencias"}

ETIQUETAS = {"prestamo": "Préstamo", "estado": "Estado", "socio": "Socio", "libro": "Libro",
             "origen": "Origen", "destino": "Destino", "sede": "Sede",
             "vencimiento": "Vencimiento", "devolucion": "Devolución",
             "dias_atraso": "Días de atraso", "multa": "Multa", "multas": "Multas",
             "activos": "Activos", "vencidos": "Vencidos",
             "prestamos_con_atraso": "Préstamos con atraso", "multa_total": "Multa total",
             "propios": "Inventario propio", "presentes": "Ubicación registrada",
             "disponibles_para_prestar": "Disponibles para prestar",
             "propios_disponibles": "Propios disponibles",
             "propios_comprometidos": "Propios comprometidos",
             "propios_prestados": "Propios prestados",
             "propios_en_transito": "Propios en tránsito",
             "propios_en_reparacion": "Propios en reparación",
             "propios_fuera_servicio": "Propios fuera de servicio",
             "propios_extraviados": "Propios extraviados",
             "prestamos": "Préstamos", "porcentaje": "Porcentaje",
             "envios": "Envíos", "pendientes": "Pendientes", "en_transito": "En tránsito",
             "recibidos_sin_novedad": "Recibidos sin novedad",
             "recibidos_con_danio": "Recibidos con daño", "extraviados": "Extraviados",
             "cancelados": "Cancelados", "tasa_envios_exitosos": "Tasa de envíos exitosos",
             "promedio_segundos_transito": "Tránsito efectivo medio"}

ESTADOS = {"activo": "Activo", "devuelto": "Devuelto", "retornando": "Retornando"}

# Las columnas con nombres ocupan el doble de ancho que las de cantidades.
COLUMNAS_ANCHAS = ("socio", "libro", "origen", "destino", "sede")


def numero(valor, decimales=0):
    """Formato argentino: punto para los miles y coma para los decimales."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "#").replace(".", ",").replace("#", ".")


def fecha_argentina(valor):
    fecha, _, hora = valor.partition("T")
    anio, mes, dia = fecha.split("-")
    return f"{dia}/{mes}/{anio}" + (f" {hora[:8]}" if hora else "")


def duracion(segundos):
    # Como en la pantalla: no se redondea a cero un tránsito corto.
    horas = int(segundos // 3600)
    minutos = int(segundos % 3600 // 60)
    resto = f"{segundos - horas * 3600 - minutos * 60:.6f}".rstrip("0").rstrip(".").replace(".", ",")
    return (f"{horas} h " if horas else "") + (f"{minutos} min " if minutos else "") + f"{resto} s"


def formatear(campo, valor):
    if valor is None:
        if campo == "tasa_envios_exitosos":
            return "Sin envíos finalizados"
        if campo == "promedio_segundos_transito":
            return "Sin viajes recibidos"
        return "-"
    if campo in ("multa", "multas", "multa_total"):
        return "$ " + numero(valor)
    if campo in ("porcentaje", "tasa_envios_exitosos"):
        return numero(valor, 2) + " %"
    if campo == "promedio_segundos_transito":
        return duracion(valor)
    if campo in ("vencimiento", "devolucion"):
        return fecha_argentina(valor)
    if campo == "estado":
        return ESTADOS.get(valor, valor)
    return str(valor)


def secciones(tipo, datos):
    """Devuelve las tablas del reporte: (subtítulo, filas, columnas)."""
    if tipo == "prestamos":
        totales = [{"sede": sede, **valores} for sede, valores in datos["totales_por_sede"].items()]
        return [("Detalle de préstamos", datos["detalle"],
                 ["prestamo", "estado", "socio", "libro", "origen", "destino",
                  "vencimiento", "devolucion", "dias_atraso", "multa"]),
                ("Totales por sede de retiro", totales, ["sede", "activos", "vencidos", "multas"]),
                ("Multas acumuladas por socio", datos["multas_por_socio"],
                 ["socio", "prestamos_con_atraso", "multa_total"])]
    if tipo == "disponibilidad":
        return [("Detalle por sede y libro", datos["detalle"],
                 ["sede", "libro", "propios", "presentes", "disponibles_para_prestar",
                  "propios_disponibles", "propios_comprometidos", "propios_prestados",
                  "propios_en_transito", "propios_en_reparacion", "propios_fuera_servicio",
                  "propios_extraviados"])]
    if tipo == "solicitados":
        return [("Ranking de préstamos interbibliotecarios", datos,
                 ["libro", "prestamos", "porcentaje"])]
    return [("Envíos por sede de origen y destino", datos,
             ["origen", "destino", "envios", "pendientes", "en_transito",
              "recibidos_sin_novedad", "recibidos_con_danio", "extraviados", "cancelados",
              "tasa_envios_exitosos", "promedio_segundos_transito"])]


def texto_periodo(tipo, desde, hasta):
    if tipo == "disponibilidad":
        return "Situación actual (este reporte no usa el período)."
    if desde and hasta:
        return f"Período: del {fecha_argentina(desde)} al {fecha_argentina(hasta)}."
    if desde:
        return f"Período: desde el {fecha_argentina(desde)}."
    if hasta:
        return f"Período: hasta el {fecha_argentina(hasta)}."
    return "Período: todos los registros."


# Colores de los gráficos, los mismos que usa la pantalla.
COLORES = {"verde": (11, 122, 94), "azul": (22, 103, 179), "ambar": (224, 160, 48),
           "naranja": (214, 110, 40), "rojo": (184, 38, 47), "gris": (150, 160, 155),
           "violeta": (112, 84, 170)}

# Estados de los ejemplares propios: son excluyentes y suman el inventario propio.
SERIES_DISPONIBILIDAD = [("propios_disponibles", "Disponibles", "verde"),
                         ("propios_comprometidos", "Comprometidos", "ambar"),
                         ("propios_prestados", "Prestados", "azul"),
                         ("propios_en_transito", "En tránsito", "violeta"),
                         ("propios_en_reparacion", "En reparación", "naranja"),
                         ("propios_fuera_servicio", "Fuera de servicio", "rojo"),
                         ("propios_extraviados", "Extraviados", "gris")]
SERIES_MOVIMIENTOS = [("recibidos_sin_novedad", "Sin novedad", "verde"),
                      ("recibidos_con_danio", "Con daño", "naranja"),
                      ("extraviados", "Extraviados", "rojo"),
                      ("cancelados", "Cancelados", "gris"),
                      ("en_transito", "En tránsito", "violeta"),
                      ("pendientes", "Pendientes", "azul")]


def datos_grafico(tipo, datos):
    """Arma el gráfico de barras del reporte: (título, series, filas, formato).

    Cada serie es (clave, nombre, color) y cada fila es (etiqueta, {clave: valor}).
    No calcula nada nuevo: agrupa columnas que ya trae el resultado del reporte.
    """
    if tipo == "prestamos":
        filas = [(sede, {"multas": t["multas"]}) for sede, t in datos["totales_por_sede"].items()]
        return "Multas por sede de retiro", [("multas", "Multas", "rojo")], filas, "dinero"
    if tipo == "disponibilidad":
        por_sede = {}
        for fila in datos["detalle"]:
            totales = por_sede.setdefault(fila["sede"], {clave: 0 for clave, _, _ in SERIES_DISPONIBILIDAD})
            for clave, _, _ in SERIES_DISPONIBILIDAD:
                totales[clave] += fila[clave]
        return ("Ejemplares propios de cada sede, por estado", SERIES_DISPONIBILIDAD,
                list(por_sede.items()), "numero")
    if tipo == "solicitados":
        filas = [(f["libro"], {"prestamos": f["prestamos"]}) for f in datos]
        return "Préstamos interbibliotecarios por libro", [("prestamos", "Préstamos", "verde")], filas, "numero"
    filas = [(f"{f['origen']} > {f['destino']}", {clave: f[clave] for clave, _, _ in SERIES_MOVIMIENTOS})
             for f in datos]
    return "Resultado de los envíos por ruta", SERIES_MOVIMIENTOS, filas, "numero"


def recortar(pdf, texto, ancho):
    while texto and pdf.get_string_width(texto) > ancho:
        texto = texto[:-2] + "."
    return texto


def dos_lineas(pdf, texto, ancho):
    """Reparte la etiqueta de una columna en dos renglones como máximo."""
    lineas = [""]
    for palabra in texto.split():
        prueba = (lineas[-1] + " " + palabra).strip()
        if pdf.get_string_width(prueba) <= ancho or not lineas[-1]:
            lineas[-1] = prueba
        elif len(lineas) < 2:
            lineas.append(palabra)
        else:
            lineas[-1] = lineas[-1] + " " + palabra
    return [recortar(pdf, linea, ancho) for linea in lineas]


def dibujar_grafico(pdf, tipo, datos):
    """Columnas verticales; con varias series, cada columna se apila por estado."""
    titulo, series, filas, formato = datos_grafico(tipo, datos)
    totales = [sum(valores.values()) for _, valores in filas]
    if not filas or max(totales) == 0:
        return  # Sin valores no hay nada que comparar: quedan las tablas.
    alto_maximo, alto_valor, alto_etiqueta = 50, 5, 9
    # Cada columna ocupa un "paso" fijo; con muchas filas se achica para entrar en la hoja.
    paso = min(30, (pdf.epw - 10) / len(filas))
    ancho_columna = paso * 0.55
    leyenda = 7 if len(series) > 1 else 0
    if pdf.will_page_break(14 + alto_valor + alto_maximo + alto_etiqueta + leyenda):
        pdf.add_page()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=7.5)
    x0 = pdf.l_margin + 5
    base = pdf.get_y() + alto_valor + alto_maximo
    for i, ((etiqueta, valores), total) in enumerate(zip(filas, totales)):
        centro = x0 + i * paso + paso / 2
        x, y = centro - ancho_columna / 2, base
        for clave, _, color in series:
            alto = alto_maximo * valores[clave] / max(totales)
            if alto > 0:
                pdf.set_fill_color(*COLORES[color])
                pdf.rect(x, y - alto, ancho_columna, alto, style="F")
                y -= alto
        pdf.set_xy(centro - paso / 2, y - alto_valor)
        pdf.cell(paso, alto_valor, "$ " + numero(total) if formato == "dinero" else numero(total), align="C")
        for renglon, linea in enumerate(dos_lineas(pdf, etiqueta, paso - 2)):
            pdf.set_xy(centro - paso / 2, base + 1 + renglon * 3.5)
            pdf.cell(paso, 3.5, linea, align="C")
    # Línea de base del gráfico.
    pdf.set_draw_color(150, 160, 155)
    pdf.line(x0, base, x0 + len(filas) * paso, base)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_y(base + alto_etiqueta)
    if len(series) > 1:
        # Leyenda: un cuadrado de color por serie.
        x, y = x0, pdf.get_y()
        for _, nombre, color in series:
            pdf.set_fill_color(*COLORES[color])
            pdf.rect(x, y + 1, 3, 3, style="F")
            pdf.set_xy(x + 4, y)
            pdf.cell(0, 5, nombre)
            x += 7 + pdf.get_string_width(nombre)
        pdf.set_y(y + 6)
    # Las tablas usan el último color de relleno: se vuelve a blanco.
    pdf.set_fill_color(255, 255, 255)


class DocumentoReporte(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.cell(0, 8, f"Página {self.page_no()} de {{nb}}", align="C")


def armar_pdf(tipo, datos, desde=None, hasta=None):
    """Arma el PDF con el resultado ya calculado y lo devuelve como bytes."""
    pdf = DocumentoReporte(orientation="landscape", format="A4")
    pdf.set_title(TITULOS[tipo])
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, "Red de Bibliotecas - Préstamos interbibliotecarios", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, TITULOS[tipo], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, texto_periodo(tipo, desde, hasta), new_x="LMARGIN", new_y="NEXT")
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.cell(0, 6, f"Generado el {generado}.", new_x="LMARGIN", new_y="NEXT")
    if isinstance(datos, dict) and datos.get("aclaracion"):
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 5, datos["aclaracion"], new_x="LMARGIN", new_y="NEXT")
    dibujar_grafico(pdf, tipo, datos)
    for subtitulo, filas, columnas in secciones(tipo, datos):
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, subtitulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=8)
        if not filas:
            pdf.cell(0, 6, "Sin datos para el período elegido.", new_x="LMARGIN", new_y="NEXT")
            continue
        anchos = [2 if columna in COLUMNAS_ANCHAS else 1 for columna in columnas]
        encabezado = FontFace(emphasis="BOLD", fill_color=(225, 232, 240))
        with pdf.table(col_widths=anchos, headings_style=encabezado, line_height=5,
                       text_align="LEFT") as tabla:
            tabla.row([ETIQUETAS[columna] for columna in columnas])
            for fila in filas:
                tabla.row([formatear(columna, fila.get(columna)) for columna in columnas])
    return bytes(pdf.output())


def nombre_archivo(tipo):
    return f"reporte-{tipo}-{date.today().isoformat()}.pdf"
