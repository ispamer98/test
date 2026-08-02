// Construcción de formularios a partir de los metadatos del servidor.
// Cualquier campo añadido en app/schema.py aparece aquí sin tocar este archivo.

import { el, $$, modal, error, exito, confirmar, aviso } from './ui.js';
import { api } from './api.js';
import { estado } from './estado.js';

const TIPOS_INPUT = {
  text: 'text', int: 'number', number: 'number', money: 'number', percent: 'number',
  date: 'date', datetime: 'datetime-local', email: 'email', tel: 'tel', url: 'url',
  ip: 'text', mac: 'text', color: 'color',
};

/** Devuelve el texto legible de una referencia (p. ej. subcontrata_id -> nombre). */
export function textoRef(campo, valor) {
  if (!valor) return '';
  const lista = estado.cacheRefs[campo.ref] || [];
  const enc = lista.find((x) => String(x.id) === String(valor));
  return enc ? enc.texto : `#${valor}`;
}

/** Carga en caché las listas necesarias para los desplegables de referencia. */
export async function cargarRefs(entidad) {
  const ent = estado.meta.entidades[entidad];
  const refs = ent.fields.filter((f) => f.type === 'ref' && f.ref);
  await Promise.all(refs.map(async (f) => {
    if (estado.cacheRefs[f.ref]) return;
    const destino = estado.meta.entidades[f.ref];
    const filas = await api.listar(f.ref, destino.per_obra ? estado.obraId : null);
    estado.cacheRefs[f.ref] = filas.map((x) => ({
      id: x.id, texto: x[destino.title_field] || `#${x.id}`,
    }));
  }));
}

export function invalidarRefs(entidad) { delete estado.cacheRefs[entidad]; }

function opcionesDe(campo) {
  if (campo.options) return campo.options;
  if (campo.cat) return estado.meta.catalogos[campo.cat] || [];
  return [];
}

/** Crea el control de un campo. */
function control(campo, valor) {
  const id = `f_${campo.name}`;

  if (campo.type === 'bool') {
    return el('div', { class: 'campo-check' }, [
      el('input', { type: 'checkbox', id, name: campo.name, checked: !!valor }),
      el('label', { for: id, txt: campo.label }),
    ]);
  }

  if (campo.type === 'textarea') {
    return el('textarea', { id, name: campo.name, txt: valor ?? '' });
  }

  if (campo.type === 'select') {
    const opciones = opcionesDe(campo);
    const sel = el('select', { id, name: campo.name }, [
      el('option', { value: '', txt: '— sin definir —' }),
      ...opciones.map((o) => el('option', { value: o, txt: o, selected: String(valor) === o })),
      // Si el valor guardado ya no está en el catálogo, no se pierde.
      (valor && !opciones.includes(valor))
        ? el('option', { value: valor, txt: `${valor} (fuera de lista)`, selected: true })
        : null,
      campo.cat ? el('option', { value: '__nuevo__', txt: '➕ Añadir valor nuevo…' }) : null,
    ]);
    if (campo.cat) {
      sel.addEventListener('change', async () => {
        if (sel.value !== '__nuevo__') return;
        sel.value = valor || '';
        const { pedirTexto } = await import('./ui.js');
        const nuevo = await pedirTexto({
          titulo: `Nuevo valor para «${campo.label}»`,
          etiqueta: 'Valor',
          ayuda: 'Se guarda para todas tus obras.',
        });
        if (!nuevo) return;
        const lista = await api.addCatalogo(campo.cat, nuevo);
        estado.meta.catalogos[campo.cat] = lista;
        sel.insertBefore(el('option', { value: nuevo, txt: nuevo }), sel.lastElementChild);
        sel.value = nuevo;
        exito('Valor añadido');
      });
    }
    return sel;
  }

  if (campo.type === 'ref') {
    const lista = estado.cacheRefs[campo.ref] || [];
    return el('select', { id, name: campo.name }, [
      el('option', { value: '', txt: '— sin asignar —' }),
      ...lista.map((o) => el('option', {
        value: o.id, txt: o.texto, selected: String(valor) === String(o.id),
      })),
    ]);
  }

  const props = {
    type: TIPOS_INPUT[campo.type] || 'text',
    id, name: campo.name,
    value: valor ?? '',
    inputmode: ['number', 'money', 'percent', 'int'].includes(campo.type) ? 'decimal' : undefined,
    step: campo.type === 'int' ? '1' : (['money', 'number', 'percent'].includes(campo.type) ? 'any' : undefined),
    placeholder: campo.type === 'ip' ? '192.168.1.100'
      : campo.type === 'mac' ? 'AA:BB:CC:DD:EE:FF' : undefined,
    autocapitalize: ['email', 'url', 'ip', 'mac'].includes(campo.type) ? 'off' : undefined,
    autocorrect: 'off',
  };
  const input = el('input', props);

  // Normalización de MAC mientras se escribe.
  if (campo.type === 'mac') {
    input.addEventListener('blur', () => {
      const limpio = input.value.replace(/[^0-9a-fA-F]/g, '').toUpperCase();
      if (limpio.length === 12) input.value = limpio.match(/.{2}/g).join(':');
    });
  }
  return input;
}

function envoltorio(campo, valor) {
  if (campo.type === 'bool') {
    const c = el('div', { class: `campo ${campo.width === 2 ? 'ancho2' : ''}` }, [control(campo, valor)]);
    if (campo.help) c.appendChild(el('div', { class: 'ayuda', txt: campo.help }));
    return c;
  }
  return el('div', { class: `campo ${campo.width === 2 ? 'ancho2' : ''}` }, [
    el('label', { for: `f_${campo.name}` }, [
      campo.label,
      campo.req ? el('span', { class: 'obl', txt: ' *' }) : null,
    ]),
    control(campo, valor),
    campo.help ? el('div', { class: 'ayuda', txt: campo.help }) : null,
    el('div', { class: 'error', datos: { errorDe: campo.name } }),
  ]);
}

/** Construye el formulario completo con pestañas por grupo. */
export function construirFormulario(entidad, registro = {}) {
  const ent = estado.meta.entidades[entidad];
  const grupos = ent.groups;
  const form = el('form', { id: 'form-registro', autocomplete: 'off' });

  const paneles = {};
  for (const g of grupos) {
    const campos = ent.fields.filter((f) => f.group === g);
    if (!campos.length) continue;
    const panel = el('div', {
      class: 'form-rejilla',
      datos: { grupo: g },
      estilo: { display: g === grupos[0] ? 'grid' : 'none' },
    }, campos.map((f) => envoltorio(f, registro[f.name])));
    paneles[g] = panel;
  }

  const nombresGrupos = Object.keys(paneles);
  if (nombresGrupos.length > 1) {
    const pestanas = el('div', { class: 'pestanas' }, nombresGrupos.map((g, i) =>
      el('button', {
        type: 'button', class: `pestana ${i === 0 ? 'activa' : ''}`, txt: g,
        onClick: (e) => {
          $$('.pestana', form).forEach((p) => p.classList.remove('activa'));
          e.currentTarget.classList.add('activa');
          for (const [nombre, panel] of Object.entries(paneles)) {
            panel.style.display = nombre === g ? 'grid' : 'none';
          }
        },
      })
    ));
    form.appendChild(pestanas);
  }
  for (const panel of Object.values(paneles)) form.appendChild(panel);
  return form;
}

/** Extrae los datos del formulario en el tipo correcto. */
export function leerFormulario(entidad, form) {
  const ent = estado.meta.entidades[entidad];
  const datos = {};
  for (const f of ent.fields) {
    const n = form.elements[f.name];
    if (!n) continue;
    if (f.type === 'bool') { datos[f.name] = n.checked ? 1 : 0; continue; }
    const v = (n.value ?? '').trim();
    if (v === '' || v === '__nuevo__') { datos[f.name] = null; continue; }
    if (['number', 'money', 'percent'].includes(f.type)) {
      const x = parseFloat(v.replace(',', '.'));
      datos[f.name] = isNaN(x) ? null : x;
    } else if (['int', 'ref'].includes(f.type)) {
      const x = parseInt(v, 10);
      datos[f.name] = isNaN(x) ? null : x;
    } else {
      datos[f.name] = v;
    }
  }
  return datos;
}

const RE_IP = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;
const RE_MAC = /^([0-9A-F]{2}:){5}[0-9A-F]{2}$/i;

/** Validación en cliente. Devuelve un mapa campo -> mensaje. */
export function validar(entidad, datos) {
  const ent = estado.meta.entidades[entidad];
  const errores = {};
  for (const f of ent.fields) {
    const v = datos[f.name];
    if (f.req && (v === null || v === undefined || v === '')) {
      errores[f.name] = 'Campo obligatorio';
      continue;
    }
    if (v === null || v === undefined || v === '') continue;
    if (f.type === 'ip' && !RE_IP.test(String(v))) {
      errores[f.name] = 'Formato de IP no válido (ej. 192.168.1.100)';
    }
    if (f.type === 'mac' && !RE_MAC.test(String(v))) {
      errores[f.name] = 'Formato de MAC no válido (AA:BB:CC:DD:EE:FF)';
    }
    if (f.type === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(v))) {
      errores[f.name] = 'Correo electrónico no válido';
    }
    if (f.type === 'percent' && (v < 0 || v > 100)) {
      errores[f.name] = 'Debe estar entre 0 y 100';
    }
    if (['number', 'money', 'int'].includes(f.type) && v < 0
        && !['margen', 'desviacion'].some((s) => f.name.includes(s))) {
      errores[f.name] = 'No puede ser negativo';
    }
  }
  // Coherencia de fechas.
  const pares = [['fecha_inicio', 'fecha_fin'], ['fecha_inicio', 'fecha_fin_prevista'],
    ['fecha_entrada', 'fecha_salida']];
  for (const [a, b] of pares) {
    if (datos[a] && datos[b] && datos[a] > datos[b]) {
      errores[b] = 'La fecha de fin es anterior a la de inicio';
    }
  }
  return errores;
}

export function pintarErrores(form, errores) {
  $$('.error', form).forEach((n) => { n.textContent = ''; });
  let primero = null;
  for (const [campo, msg] of Object.entries(errores)) {
    const n = form.querySelector(`[data-error-de="${campo}"]`);
    if (n) {
      n.textContent = msg;
      if (!primero) primero = n;
    }
  }
  if (primero) {
    // Abre la pestaña que contiene el primer error.
    const panel = primero.closest('[data-grupo]');
    if (panel) {
      const grupo = panel.dataset.grupo;
      $$('.pestana', form).forEach((p) => {
        p.classList.toggle('activa', p.textContent === grupo);
      });
      $$('[data-grupo]', form).forEach((p) => {
        p.style.display = p.dataset.grupo === grupo ? 'grid' : 'none';
      });
    }
    primero.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/**
 * Abre el modal de alta/edición.
 * @param {string} entidad
 * @param {object|null} registro  null = alta
 * @param {object} opciones  { valoresIniciales, alGuardar }
 */
export async function editar(entidad, registro = null, opciones = {}) {
  const ent = estado.meta.entidades[entidad];
  await cargarRefs(entidad);

  const inicial = registro ? { ...registro } : { ...(opciones.valoresIniciales || {}) };
  if (!registro) {
    for (const f of ent.fields) {
      if (inicial[f.name] === undefined && f.default !== undefined) inicial[f.name] = f.default;
    }
  }

  const form = construirFormulario(entidad, inicial);
  const esNuevo = !registro;

  const guardar = async () => {
    const datos = leerFormulario(entidad, form);
    const errores = validar(entidad, datos);
    if (Object.keys(errores).length) {
      pintarErrores(form, errores);
      error('Revisa los campos marcados');
      return false;
    }

    // Avisos no bloqueantes propios del dominio.
    if (entidad === 'dispositivos' && datos.ip && estado.obraId) {
      try {
        const r = await api.ipLibre(estado.obraId, datos.ip, registro?.id);
        if (!r.libre) {
          const seguir = await confirmar(
            `La IP ${datos.ip} ya está asignada a: ${r.usada_por.join(', ')}. ` +
            'Dos equipos con la misma IP provocan caídas intermitentes. ¿Guardar de todos modos?',
            { titulo: 'IP duplicada', textoOk: 'Guardar igualmente' }
          );
          if (!seguir) return false;
        }
      } catch { /* la validación es un extra: si falla, no bloquea */ }
    }
    if (entidad === 'dispositivos' && datos.num_serie) {
      try {
        const r = await api.serieExiste(datos.num_serie, registro?.id);
        if (r.existe) {
          const d = r.registros[0];
          const seguir = await confirmar(
            `El número de serie ${datos.num_serie} ya está registrado en «${d.etiqueta}»` +
            `${d.obra ? ` (obra: ${d.obra})` : ''}. ¿Continuar?`,
            { titulo: 'Número de serie repetido', textoOk: 'Continuar' }
          );
          if (!seguir) return false;
        }
      } catch { /* ídem */ }
    }

    try {
      const obra = ent.per_obra ? estado.obraId : null;
      const r = esNuevo
        ? await api.crear(entidad, datos, obra)
        : await api.actualizar(entidad, registro.id, datos);
      exito(esNuevo ? `${ent.label} creada` : 'Cambios guardados');
      invalidarRefs(entidad);
      if (opciones.alGuardar) await opciones.alGuardar(r);
      return true;
    } catch (e) {
      error(e.message);
      return false;
    }
  };

  const acciones = [{ texto: 'Cancelar' }];
  if (!esNuevo) {
    acciones.push({
      texto: '🗑',
      clase: 'btn-fantasma',
      accion: async () => {
        const ok = await confirmar(
          `¿Eliminar «${registro[ent.title_field] || 'este registro'}»? No se puede deshacer.`,
          { titulo: `Eliminar ${ent.label.toLowerCase()}` }
        );
        if (!ok) return false;
        await api.borrar(entidad, registro.id);
        exito('Registro eliminado');
        invalidarRefs(entidad);
        if (opciones.alGuardar) await opciones.alGuardar(null);
        return true;
      },
    });
  }
  acciones.push({ texto: esNuevo ? 'Crear' : 'Guardar', clase: 'btn-pri', accion: guardar });

  return modal({
    titulo: esNuevo ? `Nueva ${ent.label.toLowerCase()}` : (registro[ent.title_field] || ent.label),
    cuerpo: form,
    acciones,
  });
}
