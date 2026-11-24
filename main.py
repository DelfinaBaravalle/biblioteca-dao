"""Entrada única: python main.py inicia la aplicación web."""
import argparse
from pathlib import Path

from biblioteca.web import crear_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Ruta SQLite alternativa (por ejemplo, una copia para pruebas)')
    parser.add_argument('--puerto', type=int, default=5050)
    args = parser.parse_args()
    configuracion = None
    if args.base:
        configuracion = {'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(Path(args.base).resolve())}
    app = crear_app(configuracion)
    app.run(host='127.0.0.1', port=args.puerto, debug=False)


if __name__ == '__main__':
    main()
