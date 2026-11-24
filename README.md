# TP integrador — Biblioteca (grupo G51)

Aplicación web para administrar una red de bibliotecas con préstamos locales e interbibliotecarios. El backend usa Python con Flask y una API JSON; la persistencia es SQLite mediante Flask-SQLAlchemy; la interfaz es HTML, CSS y JavaScript sin frameworks.

El código implementa el diseño del trabajo práctico grupal: la clase `Estado` para los estados de cada entidad, State para el ciclo de vida del remito, Observer para su historial y Strategy para los reportes. Las decisiones que completan el documento están al final de este archivo, en «Decisiones del grupo».

## Ejecutar

Desde la carpeta del proyecto, con Python 3.10 o posterior:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python main.py
```

Abrir [Biblioteca](http://localhost:5050). La primera vez se crea una base nueva y vacía en `instance/biblioteca_web.db`. Para usar el sistema hay que ingresar con una cuenta del personal: si la base no tiene ninguna, la pantalla pide crear el primer usuario, y las demás se administran en Administración → Usuarios (decisión 28). El servidor escucha solo en el equipo local, en el puerto 5050 (el 5000 suele estar ocupado en macOS). Ctrl+C lo detiene.

Para tener datos con los que mostrar el sistema:

```bash
python cargar_ejemplos.py
```

Agrega datos ficticios (4 sedes, 8 socios, 10 libros y 20 ejemplares) a la base de la aplicación, sin repetirlos si ya están.

Para usar otra base y otro puerto: `python main.py --base /ruta/a/otra.sqlite --puerto 5052`.

## Operaciones de la interfaz

Al abrir la aplicación se muestra el **Inicio**, con el resumen de la red: sedes activas, ejemplares disponibles, solicitudes pendientes, préstamos activos, envíos en camino y préstamos vencidos. Desde el menú:

1. **Administración:** altas y edición de sedes, socios, libros y ejemplares; habilitación, baja lógica y condición. DNI, código de catálogo, código de ejemplar y sede propietaria son fijos.
2. **Disponibilidad:** todos los ejemplares de un libro en una sede o solo los disponibles, con estado, condición, propietaria, ubicación y motivo de indisponibilidad.
3. **Solicitudes:** registro por libro, origen y destino; asignación de la primera copia disponible; cancelación.
4. **Préstamos:** seguimiento de los préstamos creados al asignar una solicitud; entrega al socio, vencimientos y devolución.
5. **Reservas:** consulta, cancelación y atención FIFO por libro y sede de retiro. Se crean solas al registrar una solicitud que no se puede asignar en el momento (decisiones 24 y 25).
6. **Remitos:** empaquetar, despachar y recibir con la condición del ejemplar al llegar; informar extravío de un remito despachado; cancelar un remito de ida antes del despacho; historial de cada remito.
7. **Devoluciones:** préstamo, sede receptora y condición física; retorno automático cuando corresponde.
8. **Reparaciones:** apertura con descripción sobre un ejemplar dañado y cierre como reparado o inutilizable.
9. **Reportes:** préstamos activos, vencidos y multas; disponibilidad por sede; libros más solicitados entre sedes; movimientos e incidencias. Se ven en pantalla y se descargan en PDF, cada uno con un gráfico de columnas.

## Recorrido de prueba

1. Crear dos sedes, un socio, un libro y un ejemplar de la sede Centro.
2. Registrar una solicitud de Centro a Norte y asignarla. Se crea el préstamo y su remito de ida.
3. Empaquetar, despachar y recibir el remito eligiendo la condición al llegar. Si llega bueno, el préstamo queda listo para retirar; si llega dañado, el préstamo se cancela.
4. En Préstamos, elegir **Entregar al socio**. Recién entonces empieza el plazo de 14 días.
5. Registrar la devolución en Norte o en otra sede activa. Si no es la propietaria, se crea el remito de retorno a Centro.
6. Completar el retorno. Si el material está dañado, queda fuera de servicio.
7. Iniciar y cerrar su reparación. Si el resultado es bueno, vuelve a estar disponible.
8. Generar los cuatro reportes. Para ver multas, el préstamo tiene que haber superado su vencimiento.

## Reglas principales

- El préstamo dura 14 días desde la entrega al socio. Recibir un remito no equivale a entregar el ejemplar.
- Multa de $500 por cada día de atraso, calculada hasta la devolución. Las multas se informan; el pago no se registra.
- Solo reciben préstamos los socios habilitados y sin préstamos vencidos.
- El ejemplar tiene que estar disponible, en buen estado, pertenecer a la sede de origen y encontrarse allí.
- No se inician operaciones con sedes dadas de baja.
- No se admiten duplicados de DNI, código de catálogo, código de ejemplar ni nombre de sede.
- Las reservas se atienden en orden de llegada por libro y sede de retiro, y pasan a atendidas cuando el libro se entrega al socio.
- Si un remito llega dañado, el ejemplar queda fuera de servicio y, si era la ida, el préstamo se cancela. Un remito despachado que no llega se informa como extraviado. Un remito de ida se puede cancelar antes del despacho.
- Un ejemplar dañado solo vuelve a prestarse después de una reparación finalizada como buena.


## Pruebas

```bash
python -m pytest -q
```

Todas las pruebas usan bases temporales. Cubren los ocho procesos, la clase `Estado`, cada transición e incidencia del remito, las reservas, las multas, los cuatro reportes, los atributos y métodos de cada clase contra el documento, la API, dos asignaciones simultáneas de la misma copia y el rollback ante errores. Hay pruebas escritas con pytest y otras con unittest; pytest ejecuta las dos.

## Organización

| Archivo | Responsabilidad |
| --- | --- |
| `main.py` | Entrada: inicia la aplicación web. |
| `biblioteca/modelos.py` | Entidades del dominio. |
| `biblioteca/estados.py` | Clase `Estado` y catálogo de estados por ámbito. |
| `biblioteca/sistema.py` | Clase `Biblioteca`: operaciones y reglas entre entidades. |
| `biblioteca/estados_remito.py` | State: acciones permitidas y estado siguiente del remito. |
| `biblioteca/observadores.py` | Observer: historial del remito. |
| `biblioteca/reportes.py` | Strategy: `GeneradorReportes` y los cuatro reportes. |
| `biblioteca/usuarios.py` | Cuentas del personal y login (decisión 28). No forman parte del modelo del dominio. |
| `biblioteca/reportes_pdf.py` | Arma el PDF con el resultado de un reporte, sin volver a calcularlo, y dibuja su gráfico de columnas. |
| `biblioteca/orm.py` | Tablas de Flask-SQLAlchemy y traducción entre filas y dominio. |
| `biblioteca/web.py` | Rutas de la API, validación de JSON y transacciones. |
| `biblioteca/validaciones.py` | Días, horarios, nombres y contactos. |
| `templates/index.html`, `static/` | Interfaz web. |
| `tests/` | Pruebas. |

## Alcance

Fuera del alcance, según el documento entregado: notificaciones externas, recomendaciones, historial de lecturas y registro del pago de multas. La autenticación también figuraba fuera del alcance, pero se agregó el login del personal a pedido de la cátedra (decisión 28). Es una aplicación académica local: en cada operación se carga el dominio completo, se aplica el cambio y se guarda en una única transacción, lo que alcanza para esta escala.

Un ejemplar que llega dañado o inutilizable en un remito de ida queda fuera de servicio, el préstamo se cancela y se crea automáticamente el remito de retorno a su sede propietaria. Al llegar, si está dañado puede repararse y volver a prestarse (decisión 19).

## Decisiones del grupo

El documento entregado no fijaba estos puntos, o se ampliaron a pedido de la cátedra. Se conserva la numeración original, porque los comentarios del código la usan («decisión 24»). Las que quedaron sin efecto o fueron reemplazadas no se listan.

**Reglas y cálculos**

1. **Multa:** $500 por cada día de atraso (`Biblioteca.MULTA_DIARIA = 500.0`). La multa es días de atraso × 500.
2. **Entregas:** `Entrega` no tiene tipo; no existe un flujo de confirmación histórica.
3. **Tasa de envíos exitosos:** recibidos sin novedad ÷ (recibidos sin novedad + recibidos con daño + extraviados). Los cancelados y los que siguen en viaje no cuentan. Sin envíos finalizados, la tasa es `None`. Ejemplo: 7 bien, 1 dañado, 1 extraviado y 1 cancelado dan 7 / 9 = 77,78 %.
4. **Corte de la multa:** `multa(tarifa_diaria, fecha_corte=None)`. Sin fecha se calcula a hoy; para un préstamo devuelto se pasa la fecha de su `Devolucion`.
5. **Multas acumuladas por socio:** el reporte incluye los préstamos activos y los devueltos con atraso. Los devueltos sin atraso y los cancelados no figuran.
8. **Fechas:** el dominio usa `date` y `datetime`, como el documento; la base las guarda como texto ISO.
11. **Libros más solicitados:** cuenta préstamos interbibliotecarios no cancelados, por su fecha de solicitud.
12. **Reservas y préstamos cancelados:** la reserva pasa a atendida cuando el libro se entrega al socio. Si el préstamo se cancela antes (envío cancelado, extraviado o dañado), la reserva sigue pendiente y conserva su lugar. Mientras el préstamo está en curso, no frena al siguiente de la fila.
13. **Reparaciones:** solo se repara un ejemplar dañado; uno inutilizable queda fuera de servicio.
14. **Período del reporte de préstamos:** los activos figuran siempre; los devueltos con atraso se filtran por la fecha de devolución.
15. **Condición al recibir:** la recepción puede empeorar la condición del ejemplar, nunca mejorarla.
19. **Ida que llega dañada:** el ejemplar queda fuera de servicio, el préstamo se cancela y se crea solo el remito de retorno a la sede propietaria. El préstamo sigue cancelado cuando ese retorno llega o se pierde.
20. **Horarios de la sede:** se validan cuando llegan como días, apertura y cierre; un horario de texto se acepta si no está vacío.

**Interfaz y alcance**

18. **Sin consola:** la única interfaz es la web. La única persistencia es el ORM.
22. **Un solo camino para crear préstamos:** el préstamo nace al asignar una solicitud.
23. **Reportes en PDF:** cada reporte se descarga en PDF con el mismo resultado de la estrategia; no hay un segundo cálculo.
24. **Reserva automática:** al registrar una solicitud que no se puede asignar en el momento (no hay copia disponible en el origen u otro socio ya espera ese libro en esa sede), se crea la reserva del socio. No se duplica si ya la tenía, y cancelar la solicitud cancela también la reserva.
25. **Sin alta manual de reservas:** la pantalla Reservas sirve para ver la fila y cancelar.
26. **Reserva «en curso»:** una reserva pendiente cuyo socio ya tiene el préstamo asignado se muestra como «En curso (préstamo #n)». En la base sigue pendiente: los estados del documento no cambian.
27. **Gráficos:** cada reporte tiene un gráfico de columnas, en la pantalla y en el PDF, que solo agrupa datos del resultado.
28. **Login del personal (amplía el alcance):** el documento dejaba la autenticación fuera del alcance, y se agregó a pedido de la cátedra. Las cuentas (usuario, nombre, hash de la contraseña y activo) no son parte del dominio. Toda la API exige una sesión activa, salvo ingresar y crear el primer usuario con la base vacía. En Administración → Usuarios se dan de alta y se desactivan cuentas.
