"""Recursos comunes de las pruebas: una base SQLite temporal por prueba."""
import pytest

from biblioteca.orm import db, guardar_dominio, cargar_dominio
from biblioteca.web import crear_app


@pytest.fixture
def recargar(tmp_path):
    """Devuelve una función que guarda el dominio con el ORM y lo vuelve a leer de la base."""
    app = crear_app({"TESTING": True,
                     "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "prueba.db")})
    with app.app_context():
        def guardar_y_cargar(sistema):
            guardar_dominio(sistema)
            db.session.commit()
            db.session.remove()
            return cargar_dominio()
        yield guardar_y_cargar
        db.session.remove()
        db.engine.dispose()
