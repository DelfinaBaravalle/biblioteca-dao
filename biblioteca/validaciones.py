"""Validaciones de ingreso de sedes y socios."""
import re

DIAS = ('Lunes a viernes', 'Lunes a sábado', 'Lunes a domingo', 'Sábados y domingos',
        'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')


def validar_nombre(nombre):
    if not any(letra.isalpha() for letra in nombre):
        raise ValueError('El nombre debe contener al menos una letra.')


def validar_contacto(contacto):
    if not any(letra.isalnum() for letra in contacto) or len(contacto) > 200:
        raise ValueError('Ingrese un contacto de hasta 200 caracteres con letras o números.')
    if '@' in contacto and not re.fullmatch(r'[^\s@]+@[^\s@]+', contacto):
        raise ValueError('El correo de contacto no es válido.')


def hora_valida(hora):
    """Formato HH:MM, entre 00:00 y 23:59."""
    if len(hora) != 5 or hora[2] != ':' or not (hora[:2] + hora[3:]).isdecimal():
        return False
    return int(hora[:2]) <= 23 and int(hora[3:]) <= 59


def armar_horarios(dias, apertura, cierre):
    if dias not in DIAS:
        raise ValueError('Seleccione días de atención válidos.')
    if not hora_valida(apertura) or not hora_valida(cierre):
        raise ValueError('Ingrese apertura y cierre con formato HH:MM, entre 00:00 y 23:59.')
    # Con formato HH:MM, comparar los textos equivale a comparar las horas.
    if apertura >= cierre:
        raise ValueError('La apertura debe ser anterior al cierre en el mismo día.')
    return f'{dias} | {apertura} a {cierre}'
