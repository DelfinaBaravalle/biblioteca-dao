"""Formato de los valores en el PDF de los reportes."""
from fpdf import FPDF

from biblioteca.reportes_pdf import armar_pdf, datos_grafico, dos_lineas, formatear, texto_periodo


def test_formato_de_montos_porcentajes_y_fechas():
    assert formatear("multa", 1500.0) == "$ 1.500"
    assert formatear("tasa_envios_exitosos", 77.78) == "77,78 %"
    assert formatear("vencimiento", "2026-11-10") == "10/11/2026"
    assert formatear("devolucion", "2026-11-13T10:20:30.123456") == "13/11/2026 10:20:30"
    assert formatear("estado", "activo") == "Activo"
    assert formatear("devolucion", None) == "-"


def test_sin_resultado_no_se_muestra_cero():
    assert formatear("tasa_envios_exitosos", None) == "Sin envíos finalizados"
    assert formatear("promedio_segundos_transito", None) == "Sin viajes recibidos"


def test_transito_corto_no_se_redondea_a_cero():
    assert formatear("promedio_segundos_transito", 0.25) == "0,25 s"
    assert formatear("promedio_segundos_transito", 7325) == "2 h 2 min 5 s"


def test_periodo():
    assert texto_periodo("disponibilidad", "2026-11-01", "2026-11-30").startswith("Situación actual")
    assert texto_periodo("movimientos", "2026-11-01", "2026-11-30") == "Período: del 01/11/2026 al 30/11/2026."
    assert texto_periodo("movimientos", None, None) == "Período: todos los registros."


def test_pdf_con_tablas_vacias():
    datos = {"aclaracion": "Multa de $500 por día de atraso.", "detalle": [],
             "totales_por_sede": {}, "multas_por_socio": []}
    assert armar_pdf("prestamos", datos).startswith(b"%PDF")


# Decisión 27: gráficos de columnas en los reportes.

def test_grafico_de_disponibilidad_suma_los_estados_por_sede():
    fila = {"sede": "Centro", "propios_disponibles": 1, "propios_comprometidos": 0, "propios_prestados": 1,
            "propios_en_transito": 0, "propios_en_reparacion": 0, "propios_fuera_servicio": 1,
            "propios_extraviados": 0}
    titulo, series, filas, formato = datos_grafico("disponibilidad", {"detalle": [fila, dict(fila)]})
    assert filas[0][0] == "Centro"
    assert filas[0][1]["propios_prestados"] == 2 and sum(filas[0][1].values()) == 6
    assert len(series) == 7 and formato == "numero"


def test_grafico_de_ranking_y_de_multas():
    _, _, filas, _ = datos_grafico("solicitados", [{"libro": "Rayuela", "libro_id": 2, "prestamos": 3, "porcentaje": 75.0}])
    assert filas == [("Rayuela", {"prestamos": 3})]
    _, _, filas, formato = datos_grafico("prestamos", {"totales_por_sede": {"Norte": {"activos": 1, "vencidos": 1, "multas": 3000.0}}})
    assert filas == [("Norte", {"multas": 3000.0})] and formato == "dinero"


def test_grafico_de_movimientos_por_ruta():
    fila = {"origen": "Centro", "destino": "Norte", "recibidos_sin_novedad": 7, "recibidos_con_danio": 1,
            "extraviados": 1, "cancelados": 1, "en_transito": 0, "pendientes": 0}
    _, series, filas, _ = datos_grafico("movimientos", [fila])
    assert filas[0][0] == "Centro > Norte" and sum(filas[0][1].values()) == 10
    assert [s[0] for s in series][:2] == ["recibidos_sin_novedad", "recibidos_con_danio"]


def test_etiqueta_de_columna_en_dos_renglones_como_maximo():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=7.5)
    lineas = dos_lineas(pdf, "Don Quijote de la Mancha edición ilustrada", 25)
    assert 1 <= len(lineas) <= 2
    assert all(pdf.get_string_width(linea) <= 25 for linea in lineas)


def test_pdf_con_grafico_de_movimientos():
    fila = {"origen": "Centro", "destino": "Norte", "envios": 2, "pendientes": 1, "en_transito": 0,
            "recibidos_sin_novedad": 1, "recibidos_con_danio": 0, "extraviados": 0, "cancelados": 0,
            "tasa_envios_exitosos": 100.0, "promedio_segundos_transito": 3600.0}
    assert armar_pdf("movimientos", [fila] * 12).startswith(b"%PDF")
