"""Agrega datos ficticios sin borrar registros ni repetir los ejemplos existentes."""
from sqlalchemy import text
from biblioteca.web import crear_app
from biblioteca.orm import db, cargar_dominio, guardar_dominio

SEDES = [
    ("Centro", "Calle de prueba 100", "centro@biblioteca.example", "Lunes a viernes de 8 a 18"),
    ("Norte", "Calle de prueba 200", "norte@biblioteca.example", "Lunes a viernes de 9 a 17"),
    ("Sur", "Calle de prueba 300", "sur@biblioteca.example", "Lunes a viernes de 8 a 16"),
    ("Alberdi", "Calle de prueba 400", "alberdi@biblioteca.example", "Lunes a sábado de 9 a 18"),
]

SOCIOS = [
    ("90000001", "Ana Pérez", "ana@ejemplo.example"),
    ("90000002", "Lucas Gómez", "lucas@ejemplo.example"),
    ("90000003", "Sofía Martínez", "sofia@ejemplo.example"),
    ("90000004", "Mateo López", "mateo@ejemplo.example"),
    ("90000005", "Valentina Torres", "valentina@ejemplo.example"),
    ("90000006", "Tomás Ruiz", "tomas@ejemplo.example"),
    ("90000007", "Camila Fernández", "camila@ejemplo.example"),
    ("90000008", "Nicolás Díaz", "nicolas@ejemplo.example"),
]

# Estos identificadores sirven para la prueba; no son ISBN de ediciones reales.
LIBROS = [
    ("PRUEBA001", "El principito", "Antoine de Saint-Exupéry"),
    ("PRUEBA002", "Rayuela", "Julio Cortázar"),
    ("PRUEBA003", "Cien años de soledad", "Gabriel García Márquez"),
    ("PRUEBA004", "Ficciones", "Jorge Luis Borges"),
    ("PRUEBA005", "Don Quijote de la Mancha", "Miguel de Cervantes"),
    ("PRUEBA006", "Orgullo y prejuicio", "Jane Austen"),
    ("PRUEBA007", "La metamorfosis", "Franz Kafka"),
    ("PRUEBA008", "1984", "George Orwell"),
    ("PRUEBA009", "Fahrenheit 451", "Ray Bradbury"),
    ("PRUEBA010", "La invención de Morel", "Adolfo Bioy Casares"),
]


def agregar_datos_prueba(sistema):
    cantidades = {"sedes": 0, "socios": 0, "libros": 0, "ejemplares": 0}
    sedes_prueba = []
    for nombre, direccion, contacto, horarios in SEDES:
        coincidencias = [sede for sede in sistema.sedes if sede.nombre.lower() == nombre.lower()]
        if coincidencias:
            sede = coincidencias[0]
        else:
            sede = sistema.agregar_sede(nombre, direccion, contacto, horarios)
            cantidades["sedes"] += 1
        sedes_prueba.append(sede)

    for dni, nombre, contacto in SOCIOS:
        if not any(socio.dni == dni for socio in sistema.socios):
            sistema.agregar_socio(dni, nombre, contacto)
            cantidades["socios"] += 1

    for posicion, (isbn, titulo, autor) in enumerate(LIBROS):
        coincidencias = [libro for libro in sistema.libros if libro.isbn == isbn]
        if coincidencias:
            libro = coincidencias[0]
        else:
            libro = sistema.agregar_libro(isbn, titulo, autor)
            cantidades["libros"] += 1
        for copia in range(2):
            codigo = f"PRUEBA-L{posicion + 1:02d}-E{copia + 1}"
            if not any(ejemplar.codigo == codigo for ejemplar in sistema.ejemplares):
                sede = sedes_prueba[(posicion + copia) % len(sedes_prueba)]
                sistema.agregar_ejemplar(codigo, libro.id, sede.id)
                cantidades["ejemplares"] += 1
    return cantidades


def main():
    app = crear_app()
    with app.app_context():
        try:
            db.session.execute(text("BEGIN IMMEDIATE"))
            sistema = cargar_dominio()
            agregados = agregar_datos_prueba(sistema)
            guardar_dominio(sistema)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    print("Datos ficticios agregados a la misma base de la aplicación web:")
    for nombre, cantidad in agregados.items():
        print(f"  {nombre.capitalize()}: {cantidad}")


if __name__ == "__main__":
    main()
