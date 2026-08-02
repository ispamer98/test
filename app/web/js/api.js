// Capa de acceso a la API. Todo pasa por aquí para centralizar el manejo de
// errores y el corte de sesión.

export class ApiError extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

let alPerderSesion = null;
export function onSesionCaducada(fn) { alPerderSesion = fn; }

async function peticion(ruta, opciones = {}) {
  let r;
  try {
    r = await fetch(ruta, { credentials: 'same-origin', ...opciones });
  } catch {
    throw new ApiError('Sin conexión con el servidor. Comprueba que ObraSec sigue abierto.', 0);
  }
  if (r.status === 401) {
    if (alPerderSesion) alPerderSesion();
    throw new ApiError('Sesión caducada', 401);
  }
  if (!r.ok) {
    let msg = `Error ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || j.message || msg;
    } catch { /* respuesta sin JSON */ }
    throw new ApiError(msg, r.status);
  }
  if (r.status === 204) return null;
  const tipo = r.headers.get('content-type') || '';
  return tipo.includes('json') ? r.json() : r.text();
}

const json = (metodo) => (ruta, cuerpo) => peticion(ruta, {
  method: metodo,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(cuerpo ?? {}),
});

export const api = {
  get: (ruta) => peticion(ruta),
  post: json('POST'),
  put: json('PUT'),
  del: (ruta) => peticion(ruta, { method: 'DELETE' }),
  subir: (ruta, formData) => peticion(ruta, { method: 'POST', body: formData }),

  // ── atajos de dominio ──────────────────────────────────────────────
  meta: () => peticion('/api/meta'),
  estado: () => peticion('/api/estado'),
  login: (password) => json('POST')('/api/login', { password }),
  logout: () => json('POST')('/api/logout', {}),

  listar: (ent, obra, q) => {
    const p = new URLSearchParams();
    if (obra) p.set('obra', obra);
    if (q) p.set('q', q);
    return peticion(`/api/e/${ent}?${p}`);
  },
  obtener: (ent, id) => peticion(`/api/e/${ent}/${id}`),
  crear: (ent, datos, obra) => json('POST')(`/api/e/${ent}${obra ? `?obra=${obra}` : ''}`, datos),
  actualizar: (ent, id, datos) => json('PUT')(`/api/e/${ent}/${id}`, datos),
  borrar: (ent, id) => peticion(`/api/e/${ent}/${id}`, { method: 'DELETE' }),
  duplicar: (ent, id, veces) => json('POST')(`/api/e/${ent}/duplicar/${id}?veces=${veces}`, {}),

  resumen: (obra) => peticion(`/api/obras/${obra}/resumen`),
  gantt: (obra) => peticion(`/api/obras/${obra}/gantt`),
  stock: (obra) => peticion(`/api/obras/${obra}/stock`),
  panel: () => peticion('/api/panel'),
  buscar: (q, obra) => peticion(`/api/buscar?q=${encodeURIComponent(q)}${obra ? `&obra=${obra}` : ''}`),
  ipLibre: (obra, ip, excluir) =>
    peticion(`/api/obras/${obra}/ip-libre?ip=${encodeURIComponent(ip)}${excluir ? `&excluir=${excluir}` : ''}`),
  serieExiste: (serie, excluir) =>
    peticion(`/api/serie-existe?num_serie=${encodeURIComponent(serie)}${excluir ? `&excluir=${excluir}` : ''}`),

  adjuntos: (ent, id) => peticion(`/api/adjuntos?entidad=${ent}&registro_id=${id}`),
  adjuntosObra: (obra) => peticion(`/api/adjuntos?obra=${obra}`),
  borrarAdjunto: (id) => peticion(`/api/adjuntos/${id}`, { method: 'DELETE' }),

  plantillas: () => peticion('/api/plantillas'),
  borrarPlantilla: (id) => peticion(`/api/plantillas/${id}`, { method: 'DELETE' }),
  camposPlantilla: () => peticion('/api/plantillas/campos'),

  ajustes: () => peticion('/api/ajustes'),
  guardarAjustes: (datos) => json('POST')('/api/ajustes', datos),
  cambiarPassword: (password) => json('POST')('/api/ajustes/password', { password }),
  addCatalogo: (nombre, valor) => json('POST')(`/api/catalogos/${nombre}`, { valor }),

  preguntarIA: (obra_id, pregunta, historial) =>
    json('POST')('/api/ia/preguntar', { obra_id, pregunta, historial }),
  redactarIA: (obra_id, instruccion) =>
    json('POST')('/api/ia/redactar', { obra_id, instruccion }),

  importarEjecutar: (archivo, obra_id, hojas) =>
    json('POST')('/api/import/ejecutar', { archivo, obra_id, hojas }),
  crearCarpetas: (obra) => json('POST')(`/api/obras/${obra}/carpetas`, {}),
  log: (obra) => peticion(`/api/log${obra ? `?obra=${obra}` : ''}`),
};
