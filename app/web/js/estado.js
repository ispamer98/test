// Estado compartido de la aplicación.
// Se mantiene deliberadamente pequeño: metadatos, obra activa y cachés.

export const estado = {
  meta: null,          // esquema completo devuelto por /api/meta
  obraId: null,        // obra activa
  obra: null,          // ficha de la obra activa
  obras: [],           // lista de obras
  vista: 'panel',      // vista actual
  cacheRefs: {},       // entidad -> [{id, texto}] para los desplegables
  resumen: null,       // último cuadro de mando cargado
  ia: false,           // hay clave de API configurada
};

const CLAVE_OBRA = 'obrasec.obra';
const CLAVE_TEMA = 'obrasec.tema';

export function recordarObra(id) {
  estado.obraId = id;
  try { localStorage.setItem(CLAVE_OBRA, String(id ?? '')); } catch { /* modo privado */ }
}

export function obraRecordada() {
  try {
    const v = localStorage.getItem(CLAVE_OBRA);
    return v ? Number(v) : null;
  } catch { return null; }
}

export function tema() {
  try { return localStorage.getItem(CLAVE_TEMA) || 'auto'; } catch { return 'auto'; }
}

export function aplicarTema(valor) {
  const v = valor || tema();
  const oscuro = v === 'oscuro'
    || (v === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.tema = oscuro ? 'oscuro' : 'claro';
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = oscuro ? '#0b1120' : '#ffffff';
  try { localStorage.setItem(CLAVE_TEMA, v); } catch { /* modo privado */ }
}

export function siguienteTema() {
  const orden = ['auto', 'claro', 'oscuro'];
  const actual = tema();
  const siguiente = orden[(orden.indexOf(actual) + 1) % orden.length];
  aplicarTema(siguiente);
  return siguiente;
}
