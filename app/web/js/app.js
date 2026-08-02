// Punto de entrada: arranque, sesión, enrutado y menú.

import { api, onSesionCaducada, ApiError } from './api.js';
import { estado, recordarObra, obraRecordada, aplicarTema, siguienteTema } from './estado.js';
import {
  el, $, $$, limpiar, modal, exito, error, info, aviso, vacio, cargando, etiqueta, fecha,
} from './ui.js';
import { editar } from './forms.js';
import {
  vistaPanel, vistaMultiObra, vistaEntidad, vistaGantt, vistaEconomico, vistaObra,
  vistaFotos, abrirDetalle, dialogoInforme,
} from './views.js';
import { vistaAjustes, dialogoImportar } from './ajustes.js';
import { escanearEtiqueta, escanearAlbaran, abrirAsistente, comprimirImagen, dialogoSinIA } from './ia.js';

// Vistas que no salen del registro de entidades.
const VISTAS_ESPECIALES = {
  panel: { titulo: 'Cuadro de mando', icono: '📊', render: vistaPanel },
  obras: { titulo: 'Mis obras', icono: '🏗️', render: vistaMultiObra },
  obra: { titulo: 'Ficha de obra', icono: '📋', render: vistaObra },
  gantt: { titulo: 'Calendario', icono: '📅', render: vistaGantt },
  economico: { titulo: 'Económico', icono: '💶', render: vistaEconomico },
  fotos: { titulo: 'Fotos', icono: '📸', render: vistaFotos },
  ajustes: { titulo: 'Ajustes', icono: '⚙️', render: vistaAjustes },
};

// ═══════════════════════════════════════════════════════════ arranque
async function arrancar() {
  aplicarTema();

  let est;
  try {
    est = await api.estado();
  } catch {
    $('#carga').innerHTML =
      '<div class="carga-logo">⚠️</div><div class="carga-txt">No se puede contactar con ObraSec.<br>Comprueba que el programa sigue abierto.</div>';
    return;
  }

  if (est.requiere_password && !est.autenticado) return mostrarLogin();
  await iniciarApp();
}

function mostrarLogin() {
  $('#carga').classList.add('oculto');
  $('#login').classList.remove('oculto');
  const form = $('#login-form');
  const errorTxt = $('#login-error');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorTxt.textContent = '';
    const boton = form.querySelector('button');
    boton.disabled = true;
    try {
      await api.login($('#login-pass').value);
      $('#login').classList.add('oculto');
      $('#carga').classList.remove('oculto');
      await iniciarApp();
    } catch (err) {
      errorTxt.textContent = err.estado === 401 ? 'Contraseña incorrecta' : err.message;
      boton.disabled = false;
      $('#login-pass').select();
    }
  });
  setTimeout(() => $('#login-pass').focus(), 200);
}

async function iniciarApp() {
  estado.meta = await api.meta();
  estado.ia = estado.meta.ia;
  await recargarObras();

  const recordada = obraRecordada();
  if (recordada && estado.obras.some((o) => o.id === recordada)) {
    estado.obraId = recordada;
    estado.obra = estado.obras.find((o) => o.id === recordada);
  } else if (estado.obras.length === 1) {
    estado.obraId = estado.obras[0].id;
    estado.obra = estado.obras[0];
    recordarObra(estado.obraId);
  }

  construirMenu();
  conectarEventos();
  actualizarCabecera();
  $('#version').textContent = `v${estado.meta.version}`;

  $('#carga').classList.add('oculto');
  $('#app').classList.remove('oculto');

  await irA(location.hash.slice(1) || 'panel');
  registrarServiceWorker();
}

onSesionCaducada(() => {
  $('#app').classList.add('oculto');
  mostrarLogin();
});

// ═══════════════════════════════════════════════════════════════ menú
function construirMenu() {
  const menu = limpiar($('#menu'));

  const anadir = (clave, titulo, icono, contador) => {
    const b = el('button', { class: 'menu-item', datos: { vista: clave } }, [
      el('span', { txt: icono }),
      el('span', { txt: titulo, estilo: { flex: '1' } }),
      contador ? el('span', { class: 'cuenta', datos: { contadorDe: clave } }) : null,
    ]);
    menu.appendChild(b);
  };

  anadir('panel', 'Cuadro de mando', '📊');
  anadir('obras', 'Mis obras', '🏗️');
  anadir('obra', 'Ficha de la obra', '📋');

  menu.appendChild(el('div', { class: 'menu-sep', txt: 'Planificación' }));
  anadir('gantt', 'Calendario', '📅');
  anadir('tareas', 'Tareas', '✅', true);
  anadir('partes', 'Partes diarios', '🗓️', true);
  anadir('visitas', 'Visitas', '📋', true);

  menu.appendChild(el('div', { class: 'menu-sep', txt: 'Instalación' }));
  anadir('dispositivos', 'Inventario instalación', '📹', true);
  anadir('materiales', 'Materiales', '📦', true);
  anadir('consumos', 'Consumos', '📉', true);
  anadir('planos', 'Planos', '📐', true);

  menu.appendChild(el('div', { class: 'menu-sep', txt: 'Recursos' }));
  anadir('subcontratas', 'Subcontratas', '🤝', true);
  anadir('personal', 'Personal', '👷', true);
  anadir('maquinaria', 'Maquinaria', '🏗', true);

  menu.appendChild(el('div', { class: 'menu-sep', txt: 'Control' }));
  anadir('incidencias', 'Incidencias', '⚠️', true);
  anadir('documentos', 'Documentos', '📄', true);
  anadir('fotos', 'Fotos', '📸');

  menu.appendChild(el('div', { class: 'menu-sep', txt: 'Económico' }));
  anadir('economico', 'Presupuesto y costes', '💶');
  anadir('ofertas', 'Ampliaciones', '💰', true);
  anadir('certificaciones', 'Certificaciones', '🧾', true);

  menu.appendChild(el('div', { class: 'menu-sep', txt: 'General' }));
  anadir('contactos', 'Agenda', '📇');

  menu.addEventListener('click', (e) => {
    const b = e.target.closest('.menu-item');
    if (b) irA(b.dataset.vista);
  });
  $('.lateral-pie').addEventListener('click', (e) => {
    const b = e.target.closest('.menu-item');
    if (b) irA(b.dataset.vista);
  });
}

async function actualizarContadores() {
  if (!estado.obraId) {
    $$('[data-contador-de]').forEach((n) => { n.textContent = ''; });
    return;
  }
  try {
    const r = await api.resumen(estado.obraId);
    estado.resumen = r;
    const poner = (clave, valor, rojo = false) => {
      const n = $(`[data-contador-de="${clave}"]`);
      if (!n) return;
      n.textContent = valor ? String(valor) : '';
      n.classList.toggle('rojo', !!rojo && !!valor);
    };
    poner('tareas', r.tareas.total, r.tareas.retrasadas > 0);
    poner('dispositivos', r.dispositivos.total);
    poner('incidencias', r.otros.incidencias_abiertas, r.otros.incidencias_abiertas > 0);
    poner('documentos', r.otros.docs_pendientes, r.otros.docs_pendientes > 0);
    poner('subcontratas', r.otros.subcontratas);
    poner('personal', r.otros.personal);
    poner('maquinaria', r.otros.maquinaria);

    const criticas = r.alertas.filter((a) => a.severidad === 'critica').length;
    $('#btn-ia').classList.toggle('punto', criticas > 0);
  } catch { /* los contadores son un extra */ }
}

// ═══════════════════════════════════════════════════════════ enrutado
export async function irA(vista) {
  const host = $('#principal');
  estado.vista = vista;
  location.hash = vista;

  $$('.menu-item').forEach((b) => b.classList.toggle('activo', b.dataset.vista === vista));
  $$('.inf-btn').forEach((b) => b.classList.toggle('activo', b.dataset.vista === vista));
  cerrarMenu();
  host.scrollTop = 0;

  try {
    if (vista === 'mas') return menuMas();
    if (vista === 'importar') { dialogoImportar(); return irA('ajustes'); }

    const especial = VISTAS_ESPECIALES[vista];
    if (especial) {
      await especial.render(host);
    } else if (estado.meta.entidades[vista]) {
      await vistaEntidad(host, vista);
    } else {
      await vistaPanel(host);
    }
  } catch (e) {
    limpiar(host).appendChild(vacio({
      icono: '⚠️', titulo: 'Algo ha fallado', texto: e.message,
      accion: { texto: 'Reintentar', alPulsar: () => irA(vista) },
    }));
  }
  actualizarContadores();
}

function menuMas() {
  const opciones = [
    ['📋', 'Ficha de la obra', () => irA('obra')],
    ['📅', 'Calendario', () => irA('gantt')],
    ['📦', 'Materiales', () => irA('materiales')],
    ['📉', 'Consumos', () => irA('consumos')],
    ['🗓️', 'Partes diarios', () => irA('partes')],
    ['⚠️', 'Incidencias', () => irA('incidencias')],
    ['🤝', 'Subcontratas', () => irA('subcontratas')],
    ['👷', 'Personal', () => irA('personal')],
    ['🏗', 'Maquinaria', () => irA('maquinaria')],
    ['📄', 'Documentos', () => irA('documentos')],
    ['📐', 'Planos', () => irA('planos')],
    ['📋', 'Visitas', () => irA('visitas')],
    ['💶', 'Económico', () => irA('economico')],
    ['💰', 'Ampliaciones', () => irA('ofertas')],
    ['🧾', 'Certificaciones', () => irA('certificaciones')],
    ['📸', 'Fotos', () => irA('fotos')],
    ['📇', 'Agenda', () => irA('contactos')],
    ['📋', 'Escanear albarán', () => escanearAlbaran({ alCrear: () => irA('materiales') })],
    ['📄', 'Generar informe', dialogoInforme],
    ['📊', 'Exportar a Excel', () => {
      if (!estado.obraId) return error('Selecciona una obra');
      window.location.href = `/api/export/obra/${estado.obraId}`;
    }],
    ['⚙️', 'Ajustes', () => irA('ajustes')],
  ];
  const m = modal({
    titulo: 'Más opciones',
    cuerpo: el('div', { class: 'selector-lista' }, opciones.map(([ic, txt, fn]) =>
      el('div', {
        class: 'selector-item',
        onClick: () => { m.cerrar(); fn(); },
      }, [
        el('span', { txt: ic, estilo: { fontSize: '20px', width: '28px' } }),
        el('strong', { txt }),
      ])
    )),
    acciones: [{ texto: 'Cerrar' }],
    alCerrar: () => { if (estado.vista === 'mas') irA('panel'); },
  });
}

// ═══════════════════════════════════════════════════════════════ obras
export async function recargarObras(abrirUltima = false) {
  estado.obras = await api.listar('obras');
  if (abrirUltima && estado.obras.length) {
    const nueva = estado.obras.reduce((a, b) => (a.id > b.id ? a : b));
    await seleccionarObra(nueva.id);
    return;
  }
  if (estado.obraId) {
    estado.obra = estado.obras.find((o) => o.id === estado.obraId) || null;
    if (!estado.obra) { estado.obraId = null; recordarObra(null); }
  }
  actualizarCabecera();
}

export async function seleccionarObra(id) {
  estado.obraId = id;
  estado.obra = estado.obras.find((o) => o.id === id) || await api.obtener('obras', id);
  estado.cacheRefs = {};
  recordarObra(id);
  actualizarCabecera();
  await irA('panel');
}

function actualizarCabecera() {
  const o = estado.obra;
  $('#obra-nombre').textContent = o ? o.nombre : 'Ninguna obra seleccionada';
  $('#obra-sub').textContent = o
    ? [o.codigo, o.cliente, o.poblacion].filter(Boolean).join(' · ') || o.estado || ''
    : 'Pulsa para elegir o crear una';
}

function selectorObra() {
  const cuerpo = el('div', { class: 'selector-lista' });
  if (!estado.obras.length) {
    cuerpo.appendChild(el('p', { class: 'kpi-pie', estilo: { padding: '16px' }, txt: 'Todavía no hay ninguna obra.' }));
  }
  for (const o of estado.obras) {
    cuerpo.appendChild(el('div', {
      class: 'selector-item',
      onClick: () => { m.cerrar(); seleccionarObra(o.id); },
    }, [
      el('span', { txt: o.id === estado.obraId ? '✅' : '🏗️', estilo: { fontSize: '20px' } }),
      el('div', { estilo: { flex: '1', minWidth: '0' } }, [
        el('strong', { txt: o.nombre }),
        el('small', { txt: [o.codigo, o.cliente, o.poblacion].filter(Boolean).join(' · ') }),
      ]),
      etiqueta(o.estado),
    ]));
  }
  const m = modal({
    titulo: 'Elegir obra',
    cuerpo,
    acciones: [
      { texto: 'Cerrar' },
      {
        texto: '+ Nueva obra', clase: 'btn-pri',
        accion: () => { editar('obras', null, { alGuardar: () => recargarObras(true) }); },
      },
    ],
  });
}

// ══════════════════════════════════════════════════════════ búsqueda
function dialogoBuscar() {
  const entrada = el('input', { type: 'search', placeholder: 'Buscar en toda la obra…', autocomplete: 'off' });
  const resultados = el('div', { class: 'selector-lista', estilo: { marginTop: '12px' } });
  let temporizador;

  entrada.addEventListener('input', () => {
    clearTimeout(temporizador);
    const q = entrada.value.trim();
    if (q.length < 2) return limpiar(resultados);
    temporizador = setTimeout(async () => {
      const filas = await api.buscar(q, estado.obraId);
      limpiar(resultados);
      if (!filas.length) {
        resultados.appendChild(el('p', { class: 'kpi-pie', estilo: { padding: '14px' }, txt: 'Sin resultados.' }));
        return;
      }
      for (const f of filas) {
        resultados.appendChild(el('div', {
          class: 'selector-item',
          onClick: () => { m.cerrar(); abrirDetalle(f.entidad, f.id, $('#principal')); },
        }, [
          el('span', { txt: f.icono, estilo: { fontSize: '19px' } }),
          el('div', { estilo: { flex: '1', minWidth: '0' } }, [
            el('strong', { txt: f.titulo }),
            el('small', { txt: f.plural }),
          ]),
          f.estado ? etiqueta(f.estado) : null,
        ]));
      }
    }, 260);
  });

  const m = modal({ titulo: '🔍 Buscar', cuerpo: el('div', {}, [entrada, resultados]), acciones: [{ texto: 'Cerrar' }] });
  setTimeout(() => entrada.focus(), 180);
}

// ═══════════════════════════════════════════════════════════ archivos
export function subirArchivo({ entidad, registroId, camara = false, alSubir }) {
  const entrada = camara ? $('#entrada-camara') : $('#entrada-archivo');
  if (camara) entrada.setAttribute('capture', 'environment');
  entrada.accept = camara ? 'image/*' : '';
  entrada.multiple = !!camara;
  entrada.value = '';
  const alCambiar = async () => {
    entrada.removeEventListener('change', alCambiar);
    const archivos = [...entrada.files];
    if (!archivos.length) return;
    info(`Subiendo ${archivos.length} archivo(s)…`);
    let ok = 0;
    for (const a of archivos) {
      try {
        const fd = new FormData();
        fd.append('archivo', a.type.startsWith('image/') ? await comprimirImagen(a) : a, a.name);
        fd.append('entidad', entidad);
        if (registroId) fd.append('registro_id', registroId);
        if (estado.obraId) fd.append('obra_id', estado.obraId);
        await api.subir('/api/adjuntos', fd);
        ok++;
      } catch (e) { error(`${a.name}: ${e.message}`); }
    }
    if (ok) exito(`${ok} archivo(s) subidos`);
    if (alSubir) await alSubir();
  };
  entrada.addEventListener('change', alCambiar);
  entrada.click();
}

// ═══════════════════════════════════════════════════════════ eventos
function abrirMenu() { $('#lateral').classList.add('abierto'); $('#velo').classList.add('visible'); }
function cerrarMenu() { $('#lateral').classList.remove('abierto'); $('#velo').classList.remove('visible'); }

function conectarEventos() {
  $('#btn-menu').addEventListener('click', abrirMenu);
  $('#velo').addEventListener('click', cerrarMenu);
  $('#selector-obra').addEventListener('click', selectorObra);
  $('#btn-buscar').addEventListener('click', dialogoBuscar);
  $('#btn-ia').addEventListener('click', () => {
    if (!estado.ia) return dialogoSinIA();
    abrirAsistente();
  });
  $('#btn-tema').addEventListener('click', () => {
    const t = siguienteTema();
    info(`Tema: ${{ auto: 'automático', claro: 'claro', oscuro: 'oscuro' }[t]}`);
  });
  $('#btn-camara').addEventListener('click', () => {
    escanearEtiqueta({ alCrear: () => irA('dispositivos') });
  });
  $('#inferior').addEventListener('click', (e) => {
    const b = e.target.closest('.inf-btn');
    if (b && b.dataset.vista) irA(b.dataset.vista);
  });

  window.addEventListener('hashchange', () => {
    const v = location.hash.slice(1);
    if (v && v !== estado.vista) irA(v);
  });

  // Atajos de teclado en escritorio.
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select')) return;
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); dialogoBuscar(); }
    if (e.key === '/') { e.preventDefault(); dialogoBuscar(); }
  });

  // Aviso de conexión perdida (importante en una nave con mala cobertura).
  window.addEventListener('offline', () => aviso('Sin conexión. Los cambios no se guardarán hasta recuperarla.', 'mal'));
  window.addEventListener('online', () => exito('Conexión recuperada'));
}

// ═══════════════════════════════════════════════════════ service worker
function registrarServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/sw.js').catch(() => { /* sin caché offline */ });
}

// API pública para los módulos que necesitan navegar o refrescar.
window.obrasec = {
  irA, seleccionarObra, recargarObras, subirArchivo, escanearEtiqueta, escanearAlbaran,
  abrirAsistente, actualizarContadores,
};

arrancar();
