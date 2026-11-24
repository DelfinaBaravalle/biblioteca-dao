'use strict';
let estado = {},
  vista = 'inicio',
  entidad = 'sedes';
const menu = [
  ['inicio', 'Inicio'],
  ['administracion', 'Administración'],
  ['disponibilidad', 'Disponibilidad'],
  ['solicitudes', 'Solicitudes'],
  ['prestamos', 'Préstamos'],
  ['reservas', 'Reservas'],
  ['remitos', 'Remitos'],
  ['devoluciones', 'Devoluciones'],
  ['reparaciones', 'Reparaciones'],
  ['reportes', 'Reportes']
];
const titulos = Object.fromEntries(menu);
const etiquetas = {
  id: 'ID',
  nombre: 'Nombre',
  direccion: 'Dirección',
  contacto: 'Contacto',
  horarios: 'Horarios',
  dias: 'Días de atención',
  apertura: 'Hora de apertura',
  cierre: 'Hora de cierre',
  modo: 'Mostrar',
  activa: 'Sede activa',
  usuario: 'Usuario',
  clave: 'Contraseña',
  activo: 'Activo',
  habilitado: 'Socio habilitado',
  dni: 'DNI',
  isbn: 'Código de catálogo',
  titulo: 'Título',
  autor: 'Autor',
  codigo: 'Código',
  libro_id: 'Libro',
  socio_id: 'Socio',
  ejemplar_id: 'Ejemplar',
  sede_id: 'Sede',
  ubicacion_id: 'Ubicación',
  origen_id: 'Sede de origen',
  destino_id: 'Sede de retiro',
  prestamo_id: 'Préstamo',
  estado: 'Estado',
  condicion: 'Condición física',
  fecha: 'Fecha',
  fecha_solicitud: 'Fecha de solicitud',
  inicio: 'Inicio',
  disponible: 'Disponible para asignar',
  motivo: 'Disponibilidad y motivo',
  vencimiento: 'Vencimiento',
  devolucion: 'Fecha de devolución',
  condicion_devolucion: 'Condición al devolver',
  condicion_recepcion: 'Condición al recibir',
  recorrido: 'Recorrido',
  tipo: 'Viaje',
  descripcion: 'Descripción del trabajo',
  fin: 'Finalización',
  resultado: 'Resultado',
  historial: 'Historial',
  vencido: 'Vencido',
  accion: 'Acción',
  observacion: 'Observación',
  desde: 'Desde',
  hasta: 'Hasta',
  reporte: 'Reporte',
  libro: 'Libro',
  sede: 'Sede',
  origen: 'Origen',
  destino: 'Destino',
  pendientes: 'Pendientes',
  dias_atraso: 'Días de atraso',
  disponibles_para_prestar: 'Disponibles para prestar',
  propios_comprometidos: 'Propios comprometidos',
  propios_en_transito: 'Propios en tránsito',
  propios_fuera_servicio: 'Propios fuera de servicio',
  propios_prestados: 'Propios prestados',
  propios_en_reparacion: 'Propios en reparación',
  propios_disponibles: 'Propios disponibles (estado)',
  propios: 'Inventario propio',
  presentes: 'Ubicación registrada',
  promedio_segundos_transito: 'Tránsito efectivo medio',
  tasa_envios_exitosos: 'Tasa de envíos exitosos (%)',
  recibidos_sin_novedad: 'Recibidos sin novedad',
  recibidos_con_danio: 'Recibidos con daño',
  extraviados: 'Extraviados',
  cancelados: 'Cancelados',
  propios_extraviados: 'Propios extraviados',
  multa: 'Multa',
  multa_total: 'Multa total',
  multas: 'Multas',
  prestamos_con_atraso: 'Préstamos con atraso',
  socio: 'Socio',
  prestamo: 'Préstamo',
  prestamos: 'Préstamos',
  activos: 'Activos',
  vencidos: 'Vencidos',
  en_transito: 'En tránsito',
  envios: 'Envíos',
  solicitudes: 'Solicitudes',
  porcentaje: 'Porcentaje (%)'
};
const camposAlta = {
  sedes: ['nombre', 'direccion', 'contacto', 'dias', 'apertura', 'cierre'],
  socios: ['dni', 'nombre', 'contacto'],
  libros: ['isbn', 'titulo', 'autor'],
  ejemplares: ['codigo', 'libro_id', 'sede_id'],
  solicitudes: ['socio_id', 'libro_id', 'origen_id', 'destino_id'],
  devoluciones: ['prestamo_id', 'sede_id', 'condicion'],
  reparaciones: ['ejemplar_id', 'descripcion']
};
const columnas = {
  sedes: ['id', 'nombre', 'direccion', 'contacto', 'horarios', 'activa'],
  socios: ['id', 'dni', 'nombre', 'contacto', 'habilitado'],
  libros: ['id', 'isbn', 'titulo', 'autor'],
  ejemplares: ['id', 'codigo', 'libro_id', 'sede_id', 'ubicacion_id', 'estado', 'condicion'],
  solicitudes: ['id', 'socio_id', 'libro_id', 'origen_id', 'destino_id', 'fecha', 'estado',
    'prestamo_id'
  ],
  prestamos: ['id', 'socio_id', 'ejemplar_id', 'origen_id', 'destino_id', 'estado', 'inicio',
    'vencimiento',
    'vencido'
  ],
  reservas: ['id', 'socio_id', 'libro_id', 'sede_id', 'fecha', 'estado'],
  remitos: ['id', 'prestamo_id', 'tipo', 'recorrido', 'estado', 'condicion_recepcion', 'historial'],
  devoluciones: ['id', 'prestamo_id', 'sede_id', 'fecha', 'condicion'],
  reparaciones: ['id', 'ejemplar_id', 'descripcion', 'inicio', 'estado', 'fin', 'resultado']
};
const contenido = document.querySelector('#contenido');
const diasAtencion = ['Lunes a viernes', 'Lunes a sábado', 'Lunes a domingo', 'Sábados y domingos',
  'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'
];
let operacionPendiente = false;

function nodo(tag, texto, clase) {
  const e = document.createElement(tag);
  if (texto !== undefined) e.textContent = texto;
  if (clase) e.className = clase;
  return e;
}

// La búsqueda se conserva por colección, para no perderla cuando la tabla se vuelve a dibujar.
const busquedas = {};
const sinCoincidencias = nodo('p', 'Ningún registro coincide con la búsqueda.', 'vacio');

function aviso(texto, error = false) {
  const e = document.querySelector('#aviso');
  e.textContent = texto;
  e.className = error ? 'error' : '';
  e.hidden = false;
}
async function api(url, metodo = 'GET', datos) {
  const opciones = {
    method: metodo,
    headers: {
      'Content-Type': 'application/json'
    }
  };
  if (datos !== undefined) opciones.body = JSON.stringify(datos);
  const r = await fetch(url, opciones);
  let d;
  try {
    d = await r.json();
  } catch {
    throw new Error('El servidor no devolvió una respuesta válida.');
  }
  // Sin sesión (o con la cuenta desactivada), se vuelve al ingreso (decisión 28).
  if (r.status === 401 && !['/api/login', '/api/usuarios/primero'].includes(url)) mostrarIngreso(false);
  if (!r.ok) throw new Error(d.error || 'No se pudo completar la operación.');
  return d;
}
async function cargar() {
  estado = await api('/api/estado');
  document.querySelector('#conexion').textContent = '● API conectada';
}

function boton(texto, accion, clase = '') {
  const b = nodo('button', texto, clase);
  b.type = 'button';
  b.addEventListener('click', async () => {
    b.disabled = true;
    try {
      await accion();
    } catch (e) {
      aviso(e.message, true);
    } finally {
      b.disabled = false;
    }
  });
  return b;
}

function encabezado(titulo, descripcion) {
  const e = nodo('div', undefined, 'intro');
  e.append(nodo('h1', titulo), nodo('p', descripcion));
  contenido.append(e);
}

function panel(titulo) {
  const e = nodo('section', undefined, 'panel');
  e.append(nodo('h2', titulo));
  contenido.append(e);
  return e;
}

function relacion(campo) {
  return ({
    libro_id: 'libros',
    socio_id: 'socios',
    ejemplar_id: 'ejemplares',
    sede_id: 'sedes',
    origen_id: 'sedes',
    destino_id: 'sedes',
    ubicacion_id: 'sedes',
    prestamo_id: 'prestamos'
  })[campo];
}

function nombre(coleccion, valor) {
  const o = (estado[coleccion] || []).find(x => x.id === valor);
  if (!o) return valor === null ? 'Sin ubicación registrada' : (valor || '—');
  if (coleccion === 'prestamos')
    return `#${o.id} · ${nombre('socios',o.socio_id)} · ${nombre('ejemplares',o.ejemplar_id)}`;
  if (coleccion === 'ejemplares') return `${o.codigo} · ${nombre('libros',o.libro_id)}`;
  return `${o.nombre||o.titulo} (#${o.id})`;
}

function nombreSede(id) {
  const sede = (estado.sedes || []).find(s => s.id === id);
  return sede ? sede.nombre : '—';
}

// Recorrido del remito: la marca avanza por las paradas del ciclo de vida (patrón State).
const paradas = ['pendiente', 'empaquetado', 'despachado', 'recibido'];
let remitoAnimado = null;

function posicionRemito(remito) {
  if (paradas.includes(remito.estado)) return paradas.indexOf(remito.estado);
  // Extraviado o cancelado: el recorrido se corta después de la última parada alcanzada.
  const alcanzadas = remito.historial.map(h => h.estado).filter(e => paradas.includes(e));
  const ultima = paradas.indexOf(alcanzadas[alcanzadas.length - 1] || 'pendiente');
  return remito.estado === 'extraviado' ? ultima + 0.5 : ultima;
}

function recorrido(remito) {
  const e = nodo('div', undefined, 'recorrido');
  const via = nodo('div', undefined, 'via');
  const posicion = posicionRemito(remito);
  const corte = ['extraviado', 'cancelado'].includes(remito.estado);
  via.setAttribute('role', 'img');
  via.setAttribute('aria-label', `De ${nombreSede(remito.origen_id)} a ${nombreSede(remito.destino_id)}: ${remito.estado}`);
  paradas.forEach((parada, i) => {
    const punto = nodo('span', undefined, i <= posicion ? 'parada alcanzada' : 'parada');
    punto.style.left = `${i / 3 * 100}%`;
    punto.title = parada;
    via.append(punto);
  });
  via.append(nodo('span', corte ? remito.estado : undefined, corte ? 'posicion corte' : 'posicion'));
  // Después de una acción, la marca parte de la parada anterior y se desplaza hasta la nueva.
  const desde = remitoAnimado && remitoAnimado.id === remito.id ? remitoAnimado.desde : posicion;
  if (remitoAnimado && remitoAnimado.id === remito.id) remitoAnimado = null;
  via.style.setProperty('--paso', desde);
  if (desde !== posicion) requestAnimationFrame(() => requestAnimationFrame(() =>
    via.style.setProperty('--paso', posicion)));
  e.append(nodo('span', nombreSede(remito.origen_id), 'sede'), via,
    nodo('span', nombreSede(remito.destino_id), 'sede'));
  return e;
}

function fechaArgentina(valor) {
  if (!valor) return '—';
  const [fecha, hora] = valor.split('T');
  const [anio, mes, dia] = fecha.split('-');
  // La hora se muestra hasta los segundos (HH:MM:SS), sin las fracciones.
  return `${dia}/${mes}/${anio}` + (hora ? ` ${hora.slice(0, 8)}` : '');
}

const etiquetasEstado = {
  listo_retiro: 'Listo para retirar',
  esperando_envio: 'Esperando envío',
  en_transito: 'En tránsito',
  fuera_servicio: 'Fuera de servicio',
  en_reparacion: 'En reparación'
};

function etiquetaEstado(valor) {
  const texto = etiquetasEstado[valor] || valor.replaceAll('_', ' ');
  return texto[0].toUpperCase() + texto.slice(1);
}

function duracion(segundos) {
  if (segundos === null) return 'Sin viajes recibidos';
  const horas = Math.floor(segundos / 3600);
  const minutos = Math.floor((segundos % 3600) / 60);
  const resto = segundos - horas * 3600 - minutos * 60;
  const numero = new Intl.NumberFormat('es-AR', {
    maximumFractionDigits: 6
  }).format(resto);
  return (horas ? `${horas} h ` : '') + (minutos ? `${minutos} min ` : '') + `${numero} s`;
}

function celda(campo, valor) {
  const e = nodo('td');
  if (campo === 'recorrido') {
    e.append(recorrido(valor));
  } else if (campo === 'historial') {
    const d = nodo('details');
    d.append(nodo('summary', `${valor.length} cambios`));
    const lista = nodo('ol');
    for (const h of valor) lista.append(nodo('li',
      `${h.estado} · ${fechaArgentina(h.fecha)} · ${h.observacion}`));
    d.append(lista);
    e.append(d);
  } else if (['fecha', 'fecha_solicitud', 'inicio', 'vencimiento', 'devolucion', 'fin'
    ].includes(campo) && (typeof valor === 'string' || valor === null)) {
    // Una fecha vacía (null) se muestra como '—'.
    e.textContent = fechaArgentina(valor);
  } else if (['multa', 'multa_total', 'multas'].includes(campo) && typeof valor === 'number') {
    e.textContent = '$ ' + valor.toLocaleString('es-AR', {
      maximumFractionDigits: 2
    });
  } else if (campo === 'tasa_envios_exitosos' && valor === null) {
    e.textContent = 'Sin envíos finalizados';
  } else if (campo.startsWith('promedio_segundos')) {
    e.textContent = duracion(valor);
  } else if (relacion(campo)) {
    e.textContent = valor === null ? (campo === 'ubicacion_id' ? 'Sin ubicación registrada' : 'Sin asignar') :
      nombre(relacion(campo), valor);
  } else if (typeof valor === 'boolean') {
    e.append(nodo('span', valor ? 'Sí' : 'No', `estado ${campo==='vencido'&&valor?'vencido':''}`));
  } else if (campo === 'condicion_recepcion' && valor === null) {
    e.textContent = 'Pendiente';
  } else if (['estado', 'condicion', 'condicion_recepcion', 'resultado'].includes(campo) && valor) {
    e.append(nodo('span', etiquetaEstado(valor), `estado ${valor}`));
  } else e.textContent = valor === null ? 'Sin promedio' : (valor === '' ? '—' : String(valor));
  return e;
}

function celdaDeFila(campo, registro) {
  // El recorrido necesita el remito completo, no un solo campo.
  if (campo === 'recorrido') return celda(campo, registro);
  // Una reserva pendiente cuyo socio ya tiene el préstamo en curso (decisión 26).
  // En la base sigue pendiente: la etiqueta solo muestra lo que calcula el backend.
  if (campo === 'estado' && registro.prestamo_en_curso) {
    const e = nodo('td');
    e.append(nodo('span', `En curso (préstamo #${registro.prestamo_en_curso})`, 'estado listo_retiro'));
    return e;
  }
  return celda(campo, registro[campo]);
}

function tabla(registros, campos, acciones, etiquetasLocales = {}) {
  if (!registros.length) return nodo('p', 'No hay registros para mostrar.', 'vacio');
  const marco = nodo('div', undefined, 'tabla'),
    t = nodo('table'),
    head = nodo('thead'),
    hr = nodo('tr');
  for (const c of campos) hr.append(nodo('th', etiquetasLocales[c] || etiquetas[c] || c.replaceAll(
    '_', ' ')));
  if (acciones) hr.append(nodo('th', 'Acciones'));
  head.append(hr);
  t.append(head);
  const body = nodo('tbody');
  for (const r of registros) {
    const tr = nodo('tr');
    for (const c of campos) tr.append(celdaDeFila(c, r));
    if (acciones) {
      const td = nodo('td'),
        a = nodo('div', undefined, 'acciones');
      acciones(r, a);
      td.append(a);
      tr.append(td);
    }
    body.append(tr);
  }
  t.append(body);
  marco.append(t);
  return marco;
}

function opciones(campo, contexto) {
  const coleccion = relacion(campo);
  let filas = estado[coleccion] || [];
  if (coleccion === 'sedes') filas = filas.filter(o => o.activa);
  if (coleccion === 'socios') filas = filas.filter(o => o.habilitado);
  if (campo === 'prestamo_id') filas = filas.filter(o => o.estado === 'activo' && o.inicio);
  if (campo === 'ejemplar_id') filas = filas.filter(o => contexto === 'reparaciones' ? o.estado ===
    'fuera_servicio' && o.condicion === 'dañado' : o.estado === 'disponible' && o.condicion === 'bueno');
  return filas.map(o => [o.id, nombre(coleccion, o.id)]);
}

function formulario(destino, campos, enviar, {
  valores = {},
  contexto = '',
  texto = 'Confirmar operación',
  listas = {}
} = {}) {
  const f = nodo('form');
  for (const campo of campos) {
    const titulo = campo === 'sede_id' ? ({
      ejemplares: 'Sede propietaria',
      devoluciones: 'Sede receptora',
      reservas: 'Sede de retiro'
    } [contexto] || 'Sede de consulta') : (etiquetas[campo] || campo);
    const l = nodo('label', titulo);
    let input;
    let lista = listas[campo] || (campo === 'dias' ? diasAtencion.map(d => [d, d]) : campo ===
      'modo' ? [
        ['todos', 'Todos los ejemplares'],
        ['disponibles', 'Solo disponibles']
      ] : ['activa', 'habilitado'].includes(campo) ? [
        ['true', 'Sí'],
        ['false', 'No']
      ] : campo === 'condicion' ? [
        ['bueno', 'Bueno'],
        ['dañado', 'Dañado'],
        ['inutilizable', 'Inutilizable']
      ] : relacion(campo) ? opciones(campo, contexto) : null);
    if (lista) {
      input = nodo('select');
      input.append(new Option('Seleccione una opción', ''));
      for (const [valor, n] of lista) input.append(new Option(n, valor));
    } else {
      input = nodo('input');
      input.type = ['desde', 'hasta'].includes(campo) ? 'date' : ['apertura', 'cierre'].includes(
        campo) ? 'time' : 'text';
      if (campo === 'dni') {
        input.inputMode = 'numeric';
        input.pattern = '[0-9]{1,10}';
        input.maxLength = 10;
      }
      if (campo === 'horarios' && contexto === 'sedes') input.readOnly = true;
      if (campo === 'clave') {
        input.type = 'password';
        input.autocomplete = contexto === 'ingreso' ? 'current-password' : 'new-password';
      }
      if (campo !== 'dni') input.maxLength = 500;
    }
    input.name = campo;
    input.setAttribute('aria-label', titulo);
    input.required = !['desde', 'hasta', 'observacion'].includes(campo);
    if (valores[campo] !== undefined) input.value = String(valores[campo]);
    l.append(input);
    f.append(l);
  }
  const a = nodo('div', undefined, 'acciones'),
    b = nodo('button', texto);
  b.type = 'submit';
  a.append(b);
  f.append(a);
  if (Array.from(f.querySelectorAll('select[required]')).some(select => select.options.length ===
      1)) {
    b.disabled = true;
    destino.append(nodo('p', contexto === 'reparaciones' ?
      'No hay ejemplares dañados que puedan iniciar una reparación. Las copias inutilizables, prestadas, en tránsito o con reparación abierta no se muestran.' :
      contexto === 'devoluciones' ?
      'No hay préstamos con entrega documentada y activos. Recibir un remito no equivale a entregar el libro al socio.' :
      'No hay registros habilitados suficientes para esta operación. Revisá las secciones de administración y los estados pendientes.',
      'nota'));
  }
  if (contexto === 'solicitudes') filtrarOrigenSolicitud(f);
  f.addEventListener('submit', async e => {
    e.preventDefault();
    if (f.dataset.enviando) return;
    f.dataset.enviando = 'si';
    b.disabled = true;
    try {
      const datos = {};
      for (const [k, v] of new FormData(f)) {
        datos[k] = k.endsWith('_id') ? Number(v) : ['activa', 'habilitado'].includes(k) ?
          v === 'true' : v;
      }
      await enviar(datos);
    } catch (error) {
      aviso(error.message, true);
    } finally {
      delete f.dataset.enviando;
      b.disabled = false;
    }
  });
  destino.append(f);
  return f;
}

function filtrarOrigenSolicitud(formulario) {
  // Solo ayuda a elegir: prestar sigue validando en Python que la copia sea de la sede de origen.
  const libro = formulario.elements.libro_id;
  const origen = formulario.elements.origen_id;
  const nota = nodo('p', 'Ninguna sede activa tiene copias de este libro.', 'nota');
  nota.hidden = true;
  origen.parentElement.after(nota);

  function filtrar() {
    const seleccion = origen.value;
    origen.replaceChildren(new Option(libro.value ? 'Seleccione una opción' :
      'Primero elija el libro', ''));
    nota.hidden = true;
    if (!libro.value) return;
    const copias = estado.ejemplares.filter(e => e.libro_id === Number(libro.value));
    // Se ofrecen las sedes con copias propias aunque estén ocupadas: la solicitud puede quedar pendiente.
    const sedes = estado.sedes.filter(s => s.activa && copias.some(e => e.sede_id === s.id));
    for (const s of sedes) {
      // Mismo criterio que Ejemplar.esta_disponible en Python.
      const disponibles = copias.filter(e => e.sede_id === s.id && e.ubicacion_id === s.id &&
        e.estado === 'disponible' && e.condicion === 'bueno').length;
      const detalle = disponibles === 1 ? '1 disponible' : disponibles ? `${disponibles} disponibles` :
        'sin copias disponibles ahora';
      origen.append(new Option(`${s.nombre} (${detalle})`, s.id));
    }
    if (sedes.some(s => String(s.id) === seleccion)) origen.value = seleccion;
    else if (sedes.length === 1) origen.value = sedes[0].id;
    nota.hidden = sedes.length > 0;
  }
  libro.addEventListener('change', filtrar);
  filtrar();
}

async function operar(url, metodo, datos, mensaje) {
  if (operacionPendiente) throw new Error('Esperá a que termine la operación anterior.');
  operacionPendiente = true;
  const seccionInicial = location.hash;
  try {
    const r = await api(url, metodo, datos);
    await cargar();
    if (location.hash === seccionInicial) {
      mostrar();
      aviso(mensaje + (r.id ? ` Registro #${r.id}.` : ''));
    }
    return r;
  } finally {
    operacionPendiente = false;
  }
}

function formularioHorarios(destino, formulario) {
  const campos = nodo('fieldset');
  campos.append(nodo('legend', 'Nuevo horario (reemplazará el texto anterior solo al confirmar)'));
  for (const campo of ['dias', 'apertura', 'cierre']) {
    const titulo = etiquetas[campo];
    const etiqueta = nodo('label', titulo);
    const input = campo === 'dias' ? nodo('select') : nodo('input');
    if (campo === 'dias') {
      input.append(new Option('Seleccione días', ''));
      for (const dia of diasAtencion) input.append(new Option(dia, dia));
    } else input.type = 'time';
    input.name = campo;
    input.required = true;
    input.setAttribute('aria-label', etiquetas[campo]);
    etiqueta.append(input);
    campos.append(etiqueta);
  }
  formulario.prepend(campos);
  destino.remove();
}

function editarRegistro(coleccion, r) {
  const anterior = document.querySelector('#editor');
  if (anterior) anterior.remove();
  const p = panel(`Editar ${coleccion} · #${r.id}`);
  p.id = 'editor';
  const campos = {
    sedes: ['nombre', 'direccion', 'contacto', 'horarios', 'activa'],
    socios: ['nombre', 'contacto', 'habilitado'],
    libros: ['titulo', 'autor'],
    ejemplares: ['condicion']
  } [coleccion];
  const f = formulario(p, campos, d => {
    if (d.apertura) delete d.horarios;
    return operar(`/api/${coleccion}/${r.id}`, 'PATCH', d, 'Cambios guardados.');
  }, {
    valores: r,
    contexto: coleccion,
    texto: 'Confirmar cambios',
    listas: coleccion === 'ejemplares' && r.condicion !== 'bueno' ? {
      condicion: [
        ['dañado', 'Dañado'],
        ['inutilizable', 'Inutilizable']
      ]
    } : {}
  });
  if (coleccion === 'ejemplares' && r.condicion !== 'bueno') p.append(nodo('p',
    'Para devolver la condición a bueno, iniciá y finalizá una reparación.', 'nota'));
  p.append(boton('Cancelar edición', () => p.remove(), 'secundario'));
  if (coleccion === 'sedes') {
    const cambiar = boton('Cambiar días y horarios', () => formularioHorarios(cambiar, f),
      'secundario');
    p.append(cambiar);
    p.append(nodo('p', 'El horario anterior se conserva literalmente si no elegís reemplazarlo.',
      'nota'));
  }
  p.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });
}

function panelOperacion(titulo) {
  const anterior = document.querySelector('#operacion');
  if (anterior) anterior.remove();
  const p = panel(titulo);
  p.id = 'operacion';
  return p;
}

function mostrarHistorial(remito) {
  const p = panelOperacion(`Historial del remito #${remito.id}`);
  p.append(nodo('p',
    `${nombre('sedes',remito.origen_id)} → ${nombre('sedes',remito.destino_id)} · ${remito.tipo}`,
    'nota'));
  p.append(tabla(remito.historial, ['estado', 'fecha', 'observacion']));
  p.append(boton('Cerrar historial', () => p.remove(), 'secundario'));
  p.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });
}

function acciones(coleccion, r, a) {
  if ((['sedes', 'socios', 'libros'].includes(coleccion) || (coleccion === 'ejemplares' && [
      'disponible', 'fuera_servicio'
    ].includes(r.estado)))) a.append(boton('Editar',
    () => editarRegistro(coleccion, r), 'secundario'));
  if (['solicitudes', 'reservas'].includes(coleccion) && r.estado === 'pendiente') {
    if (coleccion === 'solicitudes') a.append(boton('Asignar disponible', () => operar(
      `/api/solicitudes/${r.id}/asignar`, 'POST', {},
      'Solicitud asignada. Consulte el préstamo y su remito.')));
    a.append(boton('Cancelar', () => operar(`/api/${coleccion}/${r.id}/cancelar`, 'POST', {},
      'Registro cancelado.'), 'peligro'));
  }
  if (coleccion === 'remitos') a.append(boton('Ver historial', () => mostrarHistorial(r),
    'secundario'));
  if (coleccion === 'remitos') {
    // Acciones que admite cada estado (patrón State); solo la ida puede cancelarse.
    const permitidas = {
      pendiente: ['empaquetar', 'cancelar'],
      empaquetado: ['despachar', 'cancelar'],
      despachado: ['recibir', 'informar_extravio']
    } [r.estado] || [];
    const titulos = {
      empaquetar: 'Empaquetar',
      despachar: 'Despachar',
      recibir: 'Recibir',
      informar_extravio: 'Informar extravío',
      cancelar: 'Cancelar envío'
    };
    for (const accion of permitidas) {
      if (accion === 'cancelar' && r.tipo !== 'ida') continue;
      a.append(boton(titulos[accion], () => {
        const p = panelOperacion(`Remito #${r.id} · ${titulos[accion]}`);
        const campos = accion === 'recibir' ? ['condicion', 'observacion'] : ['observacion'];
        formulario(p, campos, d => {
          remitoAnimado = {
            id: r.id,
            desde: posicionRemito(r)
          };
          return operar(`/api/remitos/${r.id}/avanzar`, 'POST', {
            accion,
            ...d
          }, 'Remito actualizado.');
        }, {
          texto: 'Confirmar: ' + titulos[accion].toLowerCase()
        });
        p.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
      }, ['cancelar', 'informar_extravio'].includes(accion) ? 'peligro' : ''));
    }
  }
  if (coleccion === 'prestamos' && r.estado === 'listo_retiro') {
    a.append(boton('Entregar al socio', () => {
      const p = panelOperacion(`Entrega del préstamo #${r.id}`);
      p.append(nodo('p',
        'Confirmá esta acción cuando el socio reciba físicamente el ejemplar. El plazo comienza en ese momento.',
        'nota'));
      p.append(boton('Confirmar entrega al socio', () => operar(
        `/api/prestamos/${r.id}/entregar`, 'POST', {}, 'Entrega registrada.')));
      p.append(boton('Cancelar', () => p.remove(), 'secundario'));
      p.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    }));
  }
  if (coleccion === 'prestamos' && r.estado === 'activo' && r.inicio) a.append(boton(
    'Devolver', () => {
      navegar('devoluciones');
      {
        const f = document.querySelector('form');
        if (f) {
          f.elements.prestamo_id.value = r.id;
          f.elements.sede_id.value = r.destino_id;
        }
      }
    }, 'secundario'));
  if (coleccion === 'reparaciones' && r.estado === 'abierta')
    for (const resultado of ['bueno', 'inutilizable']) a.append(boton(resultado === 'bueno' ?
      'Finalizar reparado' : 'Irreparable', () => operar(`/api/reparaciones/${r.id}/finalizar`,
        'POST', {
          resultado
        }, 'Reparación cerrada.'), resultado === 'bueno' ? '' : 'peligro'));
}

function registros(coleccion) {
  if (camposAlta[coleccion]) {
    const p = panel({
      sedes: 'Agregar sede',
      socios: 'Agregar socio',
      libros: 'Agregar libro',
      ejemplares: 'Agregar ejemplar',
      solicitudes: 'Registrar solicitud',
      devoluciones: 'Registrar devolución',
      reparaciones: 'Iniciar reparación'
    } [coleccion]);
    formulario(p, camposAlta[coleccion], async d => {
      // Al solicitar, el backend puede sumar al socio a la fila de reservas (decisión 24).
      const enFila = () => estado.reservas.filter(r => r.estado === 'pendiente' && r.socio_id ===
        d.socio_id && r.libro_id === d.libro_id && r.sede_id === d.destino_id).map(r => r.id);
      const antes = coleccion === 'solicitudes' ? enFila() : [];
      const r = await operar('/api/' + coleccion, 'POST', d, 'Operación registrada.');
      const nueva = coleccion === 'solicitudes' ? enFila().find(id => !antes.includes(id)) : undefined;
      if (nueva !== undefined && location.hash === '#solicitudes') aviso(
        `Solicitud registrada (#${r.id}). No se puede asignar ahora: el socio quedó en la fila de reservas (#${nueva}).`);
    }, {
      contexto: coleccion,
      texto: {
        sedes: 'Agregar sede',
        socios: 'Agregar socio',
        libros: 'Agregar libro',
        ejemplares: 'Agregar ejemplar',
        solicitudes: 'Registrar solicitud',
        devoluciones: 'Registrar devolución',
        reparaciones: 'Iniciar reparación'
      } [coleccion]
    });
    if (coleccion === 'devoluciones') p.append(nodo('p',
      'Seleccione la sede donde se recibe el material. Si difiere de la propietaria, se crea un remito de retorno.',
      'nota'));
  }
  const p = panel('Registros');
  const lista = tabla(estado[coleccion], columnas[coleccion].filter(c => c !== 'historial'), (r, a) =>
    acciones(coleccion, r, a), {sede_id: coleccion === 'ejemplares' ? 'Sede propietaria' : coleccion === 'devoluciones' ? 'Sede receptora' : 'Sede de retiro', inicio: coleccion === 'prestamos' ? 'Entrega / inicio' : 'Inicio de reparación'});
  if (estado[coleccion].length) p.append(buscadorDeFilas(coleccion, lista));
  p.append(lista);
  if (estado[coleccion].length) p.append(sinCoincidencias);
  filtrarFilas(lista);
}

function sinTildes(texto) {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

function buscadorDeFilas(coleccion, lista) {
  const campo = nodo('input', undefined, 'buscador');
  campo.type = 'search';
  campo.placeholder = 'Buscar…';
  campo.setAttribute('aria-label', 'Buscar en los registros');
  campo.value = busquedas[coleccion] || '';
  campo.dataset.coleccion = coleccion;
  campo.addEventListener('input', () => {
    busquedas[coleccion] = campo.value;
    filtrarFilas(lista);
  });
  return campo;
}

function filtrarFilas(lista) {
  // Solo filtra lo que se muestra: los datos ya están cargados y no se consulta al servidor.
  const campo = lista.parentElement.querySelector('.buscador');
  const buscado = campo ? sinTildes(campo.value.trim()) : '';
  let visibles = 0;
  for (const fila of lista.querySelectorAll('tbody tr')) {
    // Se busca en los datos de la fila, sin la columna de acciones.
    const texto = [...fila.cells].slice(0, -1).map(c => c.textContent).join(' ');
    fila.hidden = !sinTildes(texto).includes(buscado);
    if (!fila.hidden) visibles++;
  }
  sinCoincidencias.hidden = visibles > 0;
}

// Gráficos de los reportes: mismas series y colores que el PDF (reportes_pdf.datos_grafico).
const coloresGrafico = {
  verde: '#0b7a5e',
  azul: '#1667b3',
  ambar: '#e0a030',
  naranja: '#d66e28',
  rojo: '#b8262f',
  gris: '#96a09b',
  violeta: '#7054aa'
};
const seriesDisponibilidad = [
  ['propios_disponibles', 'Disponibles', 'verde'],
  ['propios_comprometidos', 'Comprometidos', 'ambar'],
  ['propios_prestados', 'Prestados', 'azul'],
  ['propios_en_transito', 'En tránsito', 'violeta'],
  ['propios_en_reparacion', 'En reparación', 'naranja'],
  ['propios_fuera_servicio', 'Fuera de servicio', 'rojo'],
  ['propios_extraviados', 'Extraviados', 'gris']
];
const seriesMovimientos = [
  ['recibidos_sin_novedad', 'Sin novedad', 'verde'],
  ['recibidos_con_danio', 'Con daño', 'naranja'],
  ['extraviados', 'Extraviados', 'rojo'],
  ['cancelados', 'Cancelados', 'gris'],
  ['en_transito', 'En tránsito', 'violeta'],
  ['pendientes', 'Pendientes', 'azul']
];

function datosGrafico(tipo, datos) {
  // Solo agrupa columnas que ya trae el reporte: el cálculo sigue en Python.
  if (tipo === 'prestamos') return ['Multas por sede de retiro', [['multas', 'Multas', 'rojo']],
    Object.entries(datos.totales_por_sede).map(([sede, t]) => [sede, {multas: t.multas}]), 'dinero'];
  if (tipo === 'disponibilidad') {
    const porSede = {};
    for (const fila of datos.detalle) {
      porSede[fila.sede] ||= Object.fromEntries(seriesDisponibilidad.map(([c]) => [c, 0]));
      for (const [c] of seriesDisponibilidad) porSede[fila.sede][c] += fila[c];
    }
    return ['Ejemplares propios de cada sede, por estado', seriesDisponibilidad,
      Object.entries(porSede), 'numero'];
  }
  if (tipo === 'solicitados') return ['Préstamos interbibliotecarios por libro',
    [['prestamos', 'Préstamos', 'verde']], datos.map(f => [f.libro, {prestamos: f.prestamos}]), 'numero'];
  return ['Resultado de los envíos por ruta', seriesMovimientos,
    datos.map(f => [`${f.origen} → ${f.destino}`, Object.fromEntries(seriesMovimientos.map(([c]) => [c, f[c]]))]),
    'numero'];
}

function graficoReporte(tipo, datos) {
  // Columnas verticales; con varias series, cada columna se apila por estado.
  const [titulo, series, filas, formato] = datosGrafico(tipo, datos);
  const totales = filas.map(([, v]) => Object.values(v).reduce((a, b) => a + b, 0));
  const maximo = Math.max(0, ...totales);
  if (!filas.length || maximo === 0) return null;
  const svgNs = 'http://www.w3.org/2000/svg';
  const elemento = (tag, atributos) => {
    const e = document.createElementNS(svgNs, tag);
    for (const [k, v] of Object.entries(atributos)) e.setAttribute(k, v);
    return e;
  };
  const paso = 96, columna = 52, arriba = 22, altoColumnas = 170, abajo = 40;
  const ancho = filas.length * paso, alto = arriba + altoColumnas + abajo;
  const base = arriba + altoColumnas;
  // El ancho fijo por columna evita que el gráfico se estire con pocas filas.
  const svg = elemento('svg', {viewBox: `0 0 ${ancho} ${alto}`, width: ancho, role: 'img',
    'aria-label': titulo, class: 'grafico'});
  svg.append(elemento('line', {x1: 0, y1: base, x2: ancho, y2: base, class: 'base'}));
  filas.forEach(([nombre, valores], i) => {
    const centro = i * paso + paso / 2;
    let y = base;
    for (const [clave, serie, color] of series) {
      const h = altoColumnas * valores[clave] / maximo;
      if (h <= 0) continue;
      y -= h;
      const barra = elemento('rect', {x: centro - columna / 2, y, width: columna, height: h,
        fill: coloresGrafico[color]});
      const ayuda = elemento('title', {});
      ayuda.textContent = `${serie}: ${valores[clave]}`;
      barra.append(ayuda);
      svg.append(barra);
    }
    const total = elemento('text', {x: centro, y: y - 6, 'text-anchor': 'middle', class: 'valor'});
    total.textContent = formato === 'dinero' ? '$ ' + totales[i].toLocaleString('es-AR') : totales[i];
    svg.append(total);
    // La etiqueta se parte en dos renglones como máximo.
    const palabras = nombre.split(' ');
    const mitad = palabras.length > 2 ? Math.ceil(palabras.length / 2) : palabras.length;
    [palabras.slice(0, mitad).join(' '), palabras.slice(mitad).join(' ')].filter(Boolean)
      .forEach((linea, renglon) => {
        const texto = elemento('text', {x: centro, y: base + 16 + renglon * 14, 'text-anchor': 'middle'});
        texto.textContent = linea.length > 16 ? linea.slice(0, 15) + '…' : linea;
        svg.append(texto);
      });
  });
  const caja = nodo('figure', undefined, 'figura-grafico');
  caja.append(nodo('figcaption', titulo), svg);
  if (series.length > 1) {
    const leyenda = nodo('div', undefined, 'leyenda');
    for (const [, serie, color] of series) {
      const item = nodo('span', serie);
      item.style.setProperty('--color', coloresGrafico[color]);
      leyenda.append(item);
    }
    caja.append(leyenda);
  }
  return caja;
}

function reporteVisual(destino, datos) {
  if (Array.isArray(datos)) {
    let campos = datos.length ? Object.keys(datos[0]) : [];
    if (campos.includes('libro') && campos.includes('libro_id')) campos = campos.filter(c => c !==
      'libro_id');
    if (campos.includes('promedio_segundos_transito')) campos = ['origen', 'destino', 'envios',
      'pendientes', 'en_transito', 'recibidos_sin_novedad', 'recibidos_con_danio',
      'extraviados', 'cancelados', 'tasa_envios_exitosos',
      'promedio_segundos_transito'
    ];
    if (campos.includes('multa') && campos.includes('dias_atraso')) campos = ['prestamo', 'estado',
      'socio', 'libro', 'origen', 'destino', 'vencimiento', 'devolucion', 'dias_atraso', 'multa'
    ];
    if (campos.includes('multa_total')) campos = ['socio', 'prestamos_con_atraso', 'multa_total'];
    if (campos.includes('vencidos')) campos = ['sede', 'activos', 'vencidos', 'multas'];
    destino.append(tabla(datos, campos));
    return;
  }
  for (const [k, v] of Object.entries(datos)) {
    if (typeof v === 'string') {
      destino.append(nodo('p', v, 'nota'));
      continue;
    }
    destino.append(nodo('h3', k.replaceAll('_', ' ')));
    if (Array.isArray(v)) reporteVisual(destino, v);
    else {
      const filas = Object.entries(v).map(([s, totales]) => ({
        sede: s,
        ...totales
      }));
      reporteVisual(destino, filas);
    }
  }
}

function mostrarInicio() {
  encabezado('Cada libro, en su lugar.',
    'Gestioná el catálogo, los préstamos y el recorrido de los ejemplares entre las sedes de la red.');
  const atajo = nodo('a', 'Registrar una solicitud', 'boton');
  atajo.href = '#solicitudes';
  const portada = document.querySelector('.intro');
  portada.classList.add('portada');
  portada.append(atajo);
  const resumen = nodo('div', undefined, 'resumen');
  contenido.append(resumen);
  mostrarResumen(resumen);
  const envios = panel('En camino');
  envios.append(nodo('p', 'Consultando envíos…', 'nota'));
  const vencidos = panel('Préstamos vencidos');
  vencidos.append(nodo('p', 'Consultando vencimientos…', 'nota'));
  // Al entrar se vuelven a pedir los datos: así aparecen también los cambios hechos desde otra
  // pestaña, y los dos paneles salen de la misma consulta.
  Promise.all([cargar(), api('/api/reportes/prestamos')]).then(([, reporte]) => {
    if (vista !== 'inicio') return;
    mostrarResumen(resumen);
    envios.lastChild.remove();
    mostrarEnvios(envios);
    const filas = reporte.detalle.filter(p => p.estado === 'activo' && p.dias_atraso > 0);
    vencidos.lastChild.replaceWith(filas.length ? tabla(filas, ['socio', 'libro', 'destino',
      'vencimiento', 'dias_atraso', 'multa'
    ], null, {
      destino: 'Sede de retiro'
    }) : nodo('p', 'No hay préstamos vencidos.', 'vacio'));
  }).catch(e => aviso(e.message, true));
}

// Fichas del Inicio: cada número sale de los datos ya cargados y lleva a su sección.
function mostrarResumen(destino) {
  const enCamino = estado.remitos.filter(r => !['recibido', 'extraviado', 'cancelado'].includes(r
    .estado)).length;
  const vencidos = estado.prestamos.filter(p => p.vencido).length;
  const fichas = [
    [estado.sedes.filter(s => s.activa).length, 'Sedes activas', 'administracion', ''],
    [estado.ejemplares.filter(e => e.estado === 'disponible').length, 'Ejemplares disponibles',
      'disponibilidad', 'cielo'
    ],
    [estado.solicitudes.filter(s => s.estado === 'pendiente').length, 'Solicitudes pendientes',
      'solicitudes', 'menta'
    ],
    [estado.prestamos.filter(p => p.estado === 'activo').length, 'Préstamos activos',
      'prestamos', 'sol'
    ],
    [enCamino, 'Envíos en camino', 'remitos', ''],
    [vencidos, 'Préstamos vencidos', 'reportes', 'coral' + (vencidos ? ' alerta' : '')]
  ];
  destino.replaceChildren();
  for (const [cantidad, texto, seccion, clase] of fichas) {
    const ficha = nodo('a', undefined, 'ficha ' + clase);
    ficha.href = '#' + seccion;
    ficha.append(nodo('strong', cantidad), nodo('span', texto));
    destino.append(ficha);
  }
}

function mostrarEnvios(envios) {
  const enCamino = estado.remitos.filter(r => !['recibido', 'extraviado', 'cancelado'].includes(r
    .estado));
  if (!enCamino.length) envios.append(nodo('p',
    'No hay envíos en curso. Se crean al asignar una solicitud entre dos sedes.', 'vacio'));
  for (const r of enCamino) {
    const prestamo = estado.prestamos.find(p => p.id === r.prestamo_id) || {};
    const ejemplar = estado.ejemplares.find(e => e.id === r.ejemplar_id) || {};
    const libro = estado.libros.find(l => l.id === ejemplar.libro_id) || {};
    const socio = estado.socios.find(s => s.id === prestamo.socio_id) || {};
    const fila = nodo('div', undefined, 'envio');
    const datos = nodo('div');
    datos.append(nodo('strong', libro.titulo || 'Ejemplar'), nodo('span',
      `${ejemplar.codigo}, ${r.tipo === 'ida' ? 'ida para' : 'retorno de'} ${socio.nombre}`
    ));
    fila.append(datos, recorrido(r));
    envios.append(fila);
  }
  if (enCamino.length) {
    const ver = nodo('a', 'Gestionar remitos', 'boton secundario');
    ver.href = '#remitos';
    envios.append(ver);
  }
}

function mostrar() {
  vista = location.hash.slice(1) || 'inicio';
  if (!titulos[vista]) vista = 'inicio';
  contenido.replaceChildren();
  document.querySelector('#aviso').hidden = true;
  document.querySelector('#ruta').textContent = titulos[vista];
  for (const a of document.querySelectorAll('nav a')) {
    if (a.hash === '#' + vista) a.setAttribute('aria-current', 'page');
    else a.removeAttribute('aria-current');
  }
  if (vista === 'inicio') {
    mostrarInicio();
    return;
  }
  if (vista === 'administracion') {
    encabezado('Administración',
      'Datos de la red, socios y catálogo. Los identificadores y los registros históricos se conservan.'
    );
    const pestanas = nodo('div', undefined, 'pestanas');
    for (const c of ['sedes', 'socios', 'libros', 'ejemplares', 'usuarios']) pestanas.append(boton(c[0]
      .toUpperCase() + c.slice(1), () => {
        entidad = c;
        mostrar();
      }, entidad === c ? 'activo' : ''));
    contenido.append(pestanas);
    if (entidad === 'usuarios') mostrarUsuarios();
    else registros(entidad);
    return;
  }
  if (vista === 'disponibilidad') {
    encabezado('Disponibilidad',
      'Consultá las copias disponibles o el estado completo, su pertenencia y ubicación registrada.'
    );
    const p = panel('Buscar ejemplares');
    formulario(p, ['libro_id', 'sede_id', 'modo'], async d => {
      const modo = d.modo;
      const resultadoAnterior = document.querySelector('#resultado');
      if (resultadoAnterior) resultadoAnterior.remove();
      const todos = await api('/api/disponibilidad?' + new URLSearchParams({
        ...d,
        modo: 'todos'
      }));
      if (vista !== 'disponibilidad') return;
      const filas = modo === 'todos' ? todos : todos.filter(e => e.disponible);
      const r = panel(modo === 'todos' ? 'Estado de todos los ejemplares' :
        'Ejemplares disponibles');
      r.id = 'resultado';
      if (!todos.length) r.append(nodo('p',
        'No existen ejemplares de este libro pertenecientes o ubicados en la sede consultada.',
        'vacio'));
      else if (!filas.length) r.append(nodo('p',
        `Existen ${todos.length} ejemplares, pero ninguno está disponible. Consultá todos para conocer sus motivos.`,
        'vacio'));
      else r.append(tabla(filas, [...columnas.ejemplares, 'disponible', 'motivo'], null, {
        sede_id: 'Sede propietaria',
        ubicacion_id: 'Ubicación actual registrada'
      }));
    }, {
      texto: 'Consultar'
    });
    return;
  }
  if (vista === 'reportes') {
    encabezado('Reportes de la red',
      'Cuatro perspectivas para conocer el uso del catálogo y los movimientos entre sedes.');
    const p = panel('Elegir reporte y período');
    formulario(p, ['reporte', 'desde', 'hasta'], async d => {
      const tipo = d.reporte;
      delete d.reporte;
      const resultadoAnterior = document.querySelector('#resultado');
      if (resultadoAnterior) resultadoAnterior.remove();
      const datos = await api('/api/reportes/' + tipo + '?' + new URLSearchParams(d));
      if (vista !== 'reportes') return;
      const r = panel('Resultados del reporte');
      r.id = 'resultado';
      // El PDF usa el mismo reporte y el mismo período que la tabla.
      const pdf = nodo('a', 'Descargar PDF', 'boton');
      pdf.href = '/api/reportes/' + tipo + '/pdf?' + new URLSearchParams(d);
      pdf.download = '';
      r.append(pdf);
      const grafico = graficoReporte(tipo, datos);
      if (grafico) r.append(grafico);
      reporteVisual(r, datos);
    }, {
      texto: 'Generar reporte',
      listas: {
        reporte: [
          ['prestamos', 'Préstamos activos, vencidos y multas'],
          ['disponibilidad', 'Disponibilidad por sede'],
          ['solicitados', 'Libros más solicitados entre sedes'],
          ['movimientos', 'Movimientos e incidencias']
        ]
      }
    });
    p.append(nodo('p',
      'El período es inclusivo. La disponibilidad muestra el estado actual. Sin viajes recibidos, el promedio de tránsito no se calcula; sin envíos finalizados, tampoco la tasa de envíos exitosos.',
      'nota'));
    return;
  }
  const descripciones = {
    solicitudes: 'Registrá el libro y las sedes. La asignación elige una copia disponible del origen y respeta las reservas FIFO del destino.',
    prestamos: 'Préstamos locales e interbibliotecarios, vencimientos y devoluciones. Se crean al asignar una solicitud.',
    reservas: 'La fila de espera de cada libro y sede de retiro. Las reservas se crean solas al registrar una solicitud que no se puede asignar en el momento; acá se consultan y se cancelan.',
    remitos: 'Empaquetá, despachá y recibí en orden, registrando la condición al llegar. Un remito despachado puede informarse como extraviado y uno de ida puede cancelarse antes del despacho. Cada transición conserva su fecha y observación.',
    devoluciones: 'Registrá la sede receptora y el estado físico del ejemplar, incluso cuando se devuelve en otra sede.',
    reparaciones: 'Registrá el trabajo sobre material fuera de servicio y cerralo con el resultado de la reparación.'
  };
  encabezado(titulos[vista], descripciones[vista]);
  registros(vista);
}
for (const [i, [clave, titulo]] of menu.entries()) {
  const a = nodo('a');
  a.href = '#' + clave;
  // Inicio va primero y lleva una casita; las demás secciones se numeran del 1 al 9.
  a.append(nodo('span', i === 0 ? '⌂' : String(i)), document.createTextNode(titulo));
  document.querySelector('#menu').append(a);
}

// --- Sesión del personal (decisión 28) ---
let usuarioActual = null;

function mostrarIngreso(sinUsuarios) {
  // La pantalla de ingreso reemplaza todo: sin sesión no se muestra el menú.
  estado = {};
  document.body.classList.add('sin-sesion');
  document.querySelector('#conexion').textContent = 'Sin sesión';
  contenido.replaceChildren();
  encabezado(sinUsuarios ? 'Crear el primer usuario' : 'Ingresar',
    sinUsuarios ? 'Todavía no hay cuentas del personal. Creá la primera para empezar a usar el sistema.' :
    'Ingresá con tu usuario del personal de la biblioteca.');
  const p = panel(sinUsuarios ? 'Primer usuario' : 'Iniciar sesión');
  formulario(p, sinUsuarios ? ['usuario', 'nombre', 'clave'] : ['usuario', 'clave'], async d => {
    await api(sinUsuarios ? '/api/usuarios/primero' : '/api/login', 'POST', d);
    location.replace(location.pathname);
  }, {
    contexto: sinUsuarios ? 'alta-usuario' : 'ingreso',
    texto: sinUsuarios ? 'Crear usuario e ingresar' : 'Ingresar'
  });
  if (sinUsuarios) p.append(nodo('p', 'La contraseña debe tener al menos 8 caracteres.', 'nota'));
}

function mostrarUsuarioActual(sesion) {
  usuarioActual = sesion;
  document.body.classList.remove('sin-sesion');
  const caja = nodo('span', undefined, 'sesion');
  caja.append(nodo('span', sesion.nombre), boton('Cerrar sesión', async () => {
    await api('/api/logout', 'POST', {});
    location.replace(location.pathname);
  }, 'secundario'));
  document.querySelector('#conexion').before(caja);
}

async function mostrarUsuarios() {
  const alta = panel('Agregar usuario del personal');
  formulario(alta, ['usuario', 'nombre', 'clave'], async d => {
    const nuevo = await api('/api/usuarios', 'POST', d);
    mostrar();
    aviso(`Usuario ${nuevo.usuario} creado.`);
  }, {
    contexto: 'alta-usuario',
    texto: 'Agregar usuario'
  });
  alta.append(nodo('p',
    'La contraseña debe tener al menos 8 caracteres. Se guarda cifrada: nadie puede verla, ni siquiera desde la base.',
    'nota'));
  const p = panel('Usuarios');
  const lista = await api('/api/usuarios');
  if (vista !== 'administracion' || entidad !== 'usuarios') return;
  p.append(tabla(lista, ['id', 'usuario', 'nombre', 'activo'], (u, a) => {
    // No se puede desactivar el propio usuario: el servidor también lo impide.
    if (u.id === usuarioActual.id) {
      a.append(nodo('span', 'Tu usuario', 'nota'));
      return;
    }
    const accion = u.activo ? 'desactivar' : 'activar';
    a.append(boton(u.activo ? 'Desactivar' : 'Activar', async () => {
      await api(`/api/usuarios/${u.id}/${accion}`, 'POST', {});
      mostrar();
      aviso(u.activo ? `Usuario ${u.usuario} desactivado: ya no puede ingresar.` : `Usuario ${u.usuario} activado.`);
    }, u.activo ? 'peligro' : ''));
  }));
}

function navegar(seccion) {
  location.hash = seccion;
  if (estado.sedes) mostrar();
}
document.addEventListener('click', evento => {
  const enlace = evento.target.closest('a[href^="#"]');
  if (!enlace) return;
  evento.preventDefault();
  navegar(enlace.hash.slice(1));
});
window.addEventListener('hashchange', () => {
  if (estado.sedes && (location.hash.slice(1) || 'inicio') !== vista) mostrar();
});
(async () => {
  try {
    const sesion = await api('/api/sesion');
    if (!sesion.usuario) {
      mostrarIngreso(sesion.sin_usuarios);
      return;
    }
    mostrarUsuarioActual(sesion);
    await cargar();
    // Al abrir la aplicación siempre se empieza por el Inicio.
    history.replaceState(null, '', location.pathname);
    mostrar();
  } catch (e) {
    document.querySelector('#conexion').textContent = 'Sin conexión';
    aviso(e.message, true);
  }
})();
