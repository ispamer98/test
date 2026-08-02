// Utilidades de interfaz: creación de elementos, modales, avisos y formato.

// ── creación de elementos ──────────────────────────────────────────────
export function el(tag, props = {}, hijos = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k === 'txt') n.textContent = v;
    else if (k === 'estilo') Object.assign(n.style, v);
    else if (k.startsWith('on')) n.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === 'datos') for (const [dk, dv] of Object.entries(v)) n.dataset[dk] = dv;
    else if (v !== null && v !== undefined && v !== false) n.setAttribute(k, v === true ? '' : v);
  }
  for (const h of [].concat(hijos)) {
    if (h === null || h === undefined || h === false) continue;
    n.appendChild(typeof h === 'string' || typeof h === 'number' ? document.createTextNode(String(h)) : h);
  }
  return n;
}

export const $ = (s, ctx = document) => ctx.querySelector(s);
export const $$ = (s, ctx = document) => [...ctx.querySelectorAll(s)];

export function limpiar(nodo) { while (nodo.firstChild) nodo.removeChild(nodo.firstChild); return nodo; }

export function escapar(t) {
  return String(t ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ── formato ────────────────────────────────────────────────────────────
export function eur(v) {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 });
}

export function num(v, dec = 0) {
  const n = Number(v);
  if (!isFinite(n)) return '—';
  return n.toLocaleString('es-ES', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

export function fecha(v) {
  if (!v) return '';
  const d = new Date(String(v).slice(0, 10));
  return isNaN(d) ? String(v) : d.toLocaleDateString('es-ES');
}

export function fechaCorta(v) {
  if (!v) return '';
  const d = new Date(String(v).slice(0, 10));
  return isNaN(d) ? String(v) : d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
}

export function diasHasta(v) {
  if (!v) return null;
  const d = new Date(String(v).slice(0, 10));
  if (isNaN(d)) return null;
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  return Math.round((d - hoy) / 86400000);
}

export function relativa(v) {
  const d = diasHasta(v);
  if (d === null) return '';
  if (d === 0) return 'hoy';
  if (d === 1) return 'mañana';
  if (d === -1) return 'ayer';
  return d < 0 ? `hace ${-d} días` : `en ${d} días`;
}

// Color semántico de un estado, para etiquetas y barras.
const ESTADOS_OK = ['Completada', 'Instalado', 'Probado', 'Entregado', 'Aprobada', 'Cerrada',
  'Resuelta', 'ACCESS', 'Activa', 'Finalizada', 'Cobrada', 'Facturada', 'OK', 'Sí'];
const ESTADOS_AVISO = ['En curso', 'En gestión', 'Pendiente', 'Solicitada', 'En revisión',
  'VALIDANDO', 'Enviada', 'En negociación', 'Configurado', 'Conexionado', 'Recibido en obra',
  'En proceso', 'REPONER', 'Pausada', 'En uso', 'En obra', 'Pendiente aprobación'];
const ESTADOS_MAL = ['Bloqueada', 'Cancelada', 'Abierta', 'Escalada', 'Rechazada', 'NO ACCESS',
  'Averiado', 'Pendiente sustitución', 'Caducada', 'EXCEDIDO', 'AGOTADO', 'Suspendida',
  'Vetada', 'Averiada', 'Crítica', 'Grave', 'No'];

export function claseEstado(v) {
  if (!v) return '';
  if (ESTADOS_OK.includes(v)) return 'ok';
  if (ESTADOS_MAL.includes(v)) return 'mal';
  if (ESTADOS_AVISO.includes(v)) return 'aviso';
  return '';
}

export function etiqueta(texto, clase) {
  if (texto === null || texto === undefined || texto === '') return el('span', { txt: '—' });
  return el('span', { class: `etq ${clase ?? claseEstado(texto)}`, txt: String(texto) });
}

// ── avisos (toast) ─────────────────────────────────────────────────────
export function aviso(texto, tipo = '') {
  const caja = $('#avisos');
  const n = el('div', { class: `aviso ${tipo}`, txt: texto });
  caja.appendChild(n);
  setTimeout(() => {
    n.style.transition = 'opacity .3s, transform .3s';
    n.style.opacity = '0';
    n.style.transform = 'translateY(10px)';
    setTimeout(() => n.remove(), 300);
  }, tipo === 'mal' ? 5200 : 3000);
}

export const exito = (t) => aviso(t, 'ok');
export const error = (t) => aviso(t, 'mal');
export const info = (t) => aviso(t, 'info');

// ── modales ────────────────────────────────────────────────────────────
export function modal({ titulo, cuerpo, acciones = [], ancho, alCerrar }) {
  const contenedor = $('#modales');
  const cerrar = () => {
    fondo.style.opacity = '0';
    setTimeout(() => { fondo.remove(); if (alCerrar) alCerrar(); }, 160);
  };

  const caja = el('div', { class: 'modal', estilo: ancho ? { maxWidth: ancho } : {} }, [
    el('div', { class: 'modal-cab' }, [
      el('h2', { txt: titulo }),
      el('button', { class: 'modal-cerrar', txt: '✕', onClick: cerrar, 'aria-label': 'Cerrar' }),
    ]),
    el('div', { class: 'modal-cuerpo' }, [cuerpo]),
    acciones.length ? el('div', { class: 'modal-pie' }, acciones.map((a) =>
      el('button', {
        class: `btn ${a.clase || ''}`,
        txt: a.texto,
        onClick: async (ev) => {
          const b = ev.currentTarget;
          if (a.cerrar !== false && !a.accion) return cerrar();
          b.disabled = true;
          const original = b.textContent;
          if (a.cargando !== false) b.textContent = '…';
          try {
            const r = await a.accion();
            if (r !== false) cerrar();
          } finally {
            b.disabled = false;
            b.textContent = original;
          }
        },
      })
    )) : null,
  ]);

  const fondo = el('div', {
    class: 'modal-fondo',
    onClick: (e) => { if (e.target === fondo) cerrar(); },
  }, [caja]);

  contenedor.appendChild(fondo);
  fondo.tabIndex = -1;
  const escuchaEsc = (e) => {
    if (e.key === 'Escape') { cerrar(); document.removeEventListener('keydown', escuchaEsc); }
  };
  document.addEventListener('keydown', escuchaEsc);
  return { cerrar, caja, cuerpo: $('.modal-cuerpo', caja) };
}

export function confirmar(texto, { titulo = 'Confirmar', textoOk = 'Sí, continuar', peligro = true } = {}) {
  return new Promise((resolver) => {
    let respondido = false;
    modal({
      titulo,
      cuerpo: el('p', { txt: texto, estilo: { margin: '0', lineHeight: '1.6' } }),
      acciones: [
        { texto: 'Cancelar', accion: () => { respondido = true; resolver(false); } },
        {
          texto: textoOk,
          clase: peligro ? 'btn-mal' : 'btn-pri',
          accion: () => { respondido = true; resolver(true); },
        },
      ],
      alCerrar: () => { if (!respondido) resolver(false); },
    });
  });
}

export function pedirTexto({ titulo, etiqueta: etq, valor = '', tipo = 'text', ayuda }) {
  return new Promise((resolver) => {
    const input = el('input', { type: tipo, value: valor });
    let respondido = false;
    const m = modal({
      titulo,
      cuerpo: el('div', { class: 'campo' }, [
        etq ? el('label', { txt: etq }) : null,
        input,
        ayuda ? el('div', { class: 'ayuda', txt: ayuda }) : null,
      ]),
      acciones: [
        { texto: 'Cancelar', accion: () => { respondido = true; resolver(null); } },
        { texto: 'Aceptar', clase: 'btn-pri', accion: () => { respondido = true; resolver(input.value); } },
      ],
      alCerrar: () => { if (!respondido) resolver(null); },
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { respondido = true; resolver(input.value); m.cerrar(); }
    });
    setTimeout(() => input.focus(), 120);
  });
}

// ── estados de pantalla ────────────────────────────────────────────────
export function vacio({ icono = '📭', titulo, texto, accion }) {
  return el('div', { class: 'vacio' }, [
    el('div', { class: 'vacio-icono', txt: icono }),
    el('h3', { txt: titulo }),
    texto ? el('p', { txt: texto }) : null,
    accion ? el('button', { class: 'btn btn-pri', txt: accion.texto, onClick: accion.alPulsar }) : null,
  ]);
}

export function cargando(texto = 'Cargando…') {
  return el('div', { class: 'vacio' }, [
    el('div', { class: 'girando', txt: '⏳' }),
    el('p', { txt: texto, estilo: { marginTop: '12px' } }),
  ]);
}

export function barra(pct, clase = '') {
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  return el('div', { class: `barra ${clase}` }, [el('i', { estilo: { width: `${v}%` } })]);
}

export function kpi({ etiqueta: etq, valor, pie, clase = '', pct, alPulsar }) {
  return el('div', {
    class: `kpi ${clase}`,
    estilo: alPulsar ? { cursor: 'pointer' } : {},
    onClick: alPulsar,
  }, [
    el('div', { class: 'kpi-etq', txt: etq }),
    el('div', { class: 'kpi-val', txt: String(valor) }),
    pie ? el('div', { class: 'kpi-pie', txt: pie }) : null,
    pct !== undefined ? barra(pct, clase) : null,
  ]);
}

// Descarga un fichero desde una URL de la API sin salir de la aplicación.
export function descargar(url) {
  const a = el('a', { href: url, download: '' });
  document.body.appendChild(a);
  a.click();
  a.remove();
}
