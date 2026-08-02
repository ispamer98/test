// Escáner de etiquetas y asistente de obra.

import { api } from './api.js';
import { estado } from './estado.js';
import { el, $, limpiar, modal, exito, error, info, aviso } from './ui.js';
import { editar } from './forms.js';

/** Reduce la foto antes de subirla: menos datos móviles y respuesta más rápida. */
export function comprimirImagen(archivo, maxLado = 1800, calidad = 0.86) {
  return new Promise((resolver) => {
    if (!archivo.type.startsWith('image/')) return resolver(archivo);
    const img = new Image();
    const url = URL.createObjectURL(archivo);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let { width: w, height: h } = img;
      if (Math.max(w, h) > maxLado) {
        const f = maxLado / Math.max(w, h);
        w = Math.round(w * f);
        h = Math.round(h * f);
      }
      const lienzo = document.createElement('canvas');
      lienzo.width = w;
      lienzo.height = h;
      lienzo.getContext('2d').drawImage(img, 0, 0, w, h);
      lienzo.toBlob(
        (b) => resolver(b ? new File([b], archivo.name.replace(/\.\w+$/, '.jpg'), { type: 'image/jpeg' }) : archivo),
        'image/jpeg', calidad
      );
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolver(archivo); };
    img.src = url;
  });
}

function pedirFotos({ camara = true, multiple = true } = {}) {
  return new Promise((resolver) => {
    const entrada = $('#entrada-camara');
    entrada.multiple = multiple;
    if (camara) entrada.setAttribute('capture', 'environment');
    else entrada.removeAttribute('capture');
    entrada.value = '';
    const alCambiar = () => {
      entrada.removeEventListener('change', alCambiar);
      resolver([...entrada.files]);
    };
    entrada.addEventListener('change', alCambiar);
    entrada.click();
  });
}

// ═══════════════════════════════════════════════ escáner de etiquetas
export async function escanearEtiqueta({ alCrear } = {}) {
  if (!estado.obraId) return error('Selecciona una obra antes de escanear');
  if (!estado.ia) return dialogoSinIA();

  const archivos = await pedirFotos({ camara: true });
  if (!archivos.length) return;

  const cuerpo = el('div', { class: 'escaner' });
  const m = modal({ titulo: '📷 Leyendo la etiqueta', cuerpo, acciones: [{ texto: 'Cancelar' }] });

  const vista = el('img', { class: 'escaner-vista', src: URL.createObjectURL(archivos[0]) });
  cuerpo.appendChild(vista);
  cuerpo.appendChild(el('div', { class: 'escaner-cargando' }, [
    el('div', { class: 'girando', txt: '⚙️' }),
    el('p', { txt: 'Analizando la imagen…', estilo: { marginTop: '10px', fontWeight: '600' } }),
    el('p', { class: 'kpi-pie', txt: 'Extrayendo marca, modelo, número de serie y MAC.' }),
  ]));

  let resultado;
  try {
    const comprimidas = await Promise.all(archivos.slice(0, 3).map((f) => comprimirImagen(f)));
    const fd = new FormData();
    comprimidas.forEach((f) => fd.append('archivos', f, f.name));
    fd.append('contexto',
      `Obra: ${estado.obra?.nombre || ''}. Instalación de seguridad en ${estado.obra?.tipo_instalacion || 'nave logística'}.`);
    resultado = await api.subir('/api/ia/etiqueta', fd);
  } catch (e) {
    limpiar(cuerpo).appendChild(el('div', {}, [
      el('div', { class: 'aviso-caja mal', txt: e.message }),
      el('button', {
        class: 'btn btn-ancho', txt: '✏️ Darlo de alta a mano',
        onClick: () => { m.cerrar(); editar('dispositivos', null, { alGuardar: alCrear }); },
      }),
    ]));
    return;
  }

  // Guarda la foto de la etiqueta para adjuntarla al dispositivo que se cree.
  const fotoOriginal = archivos[0];
  mostrarResultado(m, cuerpo, resultado, fotoOriginal, alCrear);
}

function mostrarResultado(m, cuerpo, resultado, foto, alCrear) {
  const campos = resultado.campos || {};
  const claves = Object.keys(campos);
  limpiar(cuerpo);

  if (!claves.length) {
    cuerpo.appendChild(el('div', { class: 'aviso-caja aviso', txt: 'No se ha podido extraer ningún dato legible de la foto.' }));
    cuerpo.appendChild(el('button', {
      class: 'btn btn-ancho', txt: '✏️ Dar de alta a mano',
      onClick: () => { m.cerrar(); editar('dispositivos', null, { alGuardar: alCrear }); },
    }));
    return;
  }

  const colorConfianza = { alta: 'ok', media: 'info', baja: 'aviso' }[resultado.confianza] || 'info';
  const textoConfianza = {
    alta: '✅ Lectura clara', media: 'ℹ️ Lectura correcta, revísala', baja: '⚠️ Lectura dudosa: comprueba los datos',
  }[resultado.confianza] || '';

  cuerpo.appendChild(el('img', { class: 'escaner-vista', src: URL.createObjectURL(foto) }));
  cuerpo.appendChild(el('div', { class: `aviso-caja ${colorConfianza}`, txt: textoConfianza }));
  if (resultado.aviso) {
    cuerpo.appendChild(el('div', { class: 'aviso-caja aviso', txt: resultado.aviso }));
  }

  const ent = estado.meta.entidades.dispositivos;
  const etiquetaDe = (n) => ent.fields.find((f) => f.name === n)?.label || n;
  cuerpo.appendChild(el('dl', { class: 'lista-def', estilo: { textAlign: 'left' } },
    claves.flatMap((k) => [
      el('dt', { txt: etiquetaDe(k) }),
      el('dd', { txt: String(campos[k]), estilo: { fontWeight: '600' } }),
    ])));

  if (resultado.texto_leido) {
    const detalle = el('details', { estilo: { marginTop: '10px', textAlign: 'left' } }, [
      el('summary', { txt: 'Ver texto leído en la etiqueta', estilo: { cursor: 'pointer', fontSize: '13px', color: 'var(--texto-2)' } }),
      el('div', { class: 'leido', txt: resultado.texto_leido }),
    ]);
    cuerpo.appendChild(detalle);
  }

  const pie = m.caja.querySelector('.modal-pie');
  limpiar(pie);
  pie.appendChild(el('button', { class: 'btn', txt: 'Repetir foto', onClick: () => { m.cerrar(); escanearEtiqueta({ alCrear }); } }));
  pie.appendChild(el('button', {
    class: 'btn btn-pri', txt: '➕ Añadir al inventario',
    onClick: async () => {
      m.cerrar();
      await editar('dispositivos', null, {
        valoresIniciales: { ...campos, estado: 'Recibido en obra' },
        alGuardar: async (reg) => {
          if (reg && foto) {
            try {
              const fd = new FormData();
              fd.append('archivo', await comprimirImagen(foto), foto.name);
              fd.append('entidad', 'dispositivos');
              fd.append('registro_id', reg.id);
              fd.append('obra_id', estado.obraId);
              fd.append('categoria', 'etiqueta');
              fd.append('descripcion', 'Foto de la etiqueta del equipo');
              await api.subir('/api/adjuntos', fd);
            } catch { /* si falla la subida, el equipo ya está creado */ }
          }
          if (alCrear) await alCrear(reg);
        },
      });
    },
  }));
}

// ═══════════════════════════════════════════════════════ albaranes
export async function escanearAlbaran({ alCrear } = {}) {
  if (!estado.obraId) return error('Selecciona una obra primero');
  if (!estado.ia) return dialogoSinIA();

  const archivos = await pedirFotos({ camara: true });
  if (!archivos.length) return;

  const cuerpo = el('div', { class: 'escaner' }, [
    el('div', { class: 'escaner-cargando' }, [
      el('div', { class: 'girando', txt: '📋' }),
      el('p', { txt: 'Leyendo el albarán…', estilo: { marginTop: '10px', fontWeight: '600' } }),
    ]),
  ]);
  const m = modal({ titulo: '📋 Recepción de material', cuerpo, acciones: [{ texto: 'Cancelar' }] });

  let r;
  try {
    const comprimidas = await Promise.all(archivos.slice(0, 5).map((f) => comprimirImagen(f, 2200)));
    const fd = new FormData();
    comprimidas.forEach((f) => fd.append('archivos', f, f.name));
    r = await api.subir('/api/ia/albaran', fd);
  } catch (e) {
    limpiar(cuerpo).appendChild(el('div', { class: 'aviso-caja mal', txt: e.message }));
    return;
  }

  const lineas = r.lineas || [];
  limpiar(cuerpo);
  if (!lineas.length) {
    cuerpo.appendChild(el('div', { class: 'aviso-caja aviso', txt: 'No se han detectado líneas de material en la foto.' }));
    return;
  }

  cuerpo.appendChild(el('div', { class: 'aviso-caja info' },
    `${r.proveedor || 'Proveedor no detectado'}${r.numero_albaran ? ` · Albarán ${r.numero_albaran}` : ''}${r.fecha ? ` · ${r.fecha}` : ''}`));
  if (r.aviso) cuerpo.appendChild(el('div', { class: 'aviso-caja aviso', txt: r.aviso }));

  const marcas = [];
  cuerpo.appendChild(el('div', { class: 'fichas', estilo: { textAlign: 'left' } }, lineas.map((l, i) => {
    const chk = el('input', { type: 'checkbox', checked: true });
    marcas.push({ chk, linea: l });
    return el('label', { class: 'ficha', estilo: { display: 'flex', gap: '10px', alignItems: 'flex-start', cursor: 'pointer' } }, [
      chk,
      el('div', { estilo: { flex: '1' } }, [
        el('div', { class: 'ficha-tit', txt: l.material }),
        el('div', { class: 'ficha-datos' }, [
          el('span', {}, [el('b', { txt: String(l.cantidad) }), ` ${l.unidad || 'ud'}`]),
          l.codigo ? el('span', { txt: l.codigo }) : null,
          l.precio ? el('span', {}, [el('b', { txt: `${l.precio} €` })]) : null,
          el('span', { txt: l.categoria }),
        ]),
      ]),
    ]);
  })));

  const pie = m.caja.querySelector('.modal-pie');
  limpiar(pie);
  pie.appendChild(el('button', { class: 'btn', txt: 'Cancelar', onClick: () => m.cerrar() }));
  pie.appendChild(el('button', {
    class: 'btn btn-pri', txt: 'Añadir al almacén',
    onClick: async () => {
      const sel = marcas.filter((x) => x.chk.checked).map((x) => x.linea);
      if (!sel.length) return error('No has marcado ninguna línea');
      const existentes = await api.listar('materiales', estado.obraId);
      const porNombre = new Map(existentes.map((m2) => [String(m2.material || '').toLowerCase().trim(), m2]));
      let nuevos = 0; let actualizados = 0;
      for (const l of sel) {
        const clave = String(l.material).toLowerCase().trim();
        const ya = porNombre.get(clave);
        if (ya) {
          await api.actualizar('materiales', ya.id, {
            recibido: Number(ya.recibido || 0) + Number(l.cantidad || 0),
            precio: l.precio || ya.precio,
            fecha_recepcion: r.fecha || new Date().toISOString().slice(0, 10),
            albaran: r.numero_albaran || ya.albaran,
          });
          actualizados++;
        } else {
          await api.crear('materiales', {
            material: l.material, codigo: l.codigo, categoria: l.categoria,
            unidad: l.unidad || 'ud', recibido: l.cantidad, precio: l.precio || null,
            proveedor: r.proveedor, albaran: r.numero_albaran,
            fecha_recepcion: r.fecha || new Date().toISOString().slice(0, 10),
          }, estado.obraId);
          nuevos++;
        }
      }
      m.cerrar();
      exito(`${nuevos} material(es) nuevos y ${actualizados} actualizados`);
      if (alCrear) await alCrear();
    },
  }));
}

// ═══════════════════════════════════════════════════════ asistente
const SUGERENCIAS = [
  '¿Qué debería vigilar hoy?',
  '¿Vamos a llegar a la fecha de entrega?',
  'Resume el estado de la obra en 5 líneas',
  '¿Qué me falta para poder firmar el acta de recepción?',
  '¿Dónde se me está yendo el dinero?',
  'Redacta el correo de seguimiento semanal para el cliente',
];

export function abrirAsistente() {
  if (!estado.obraId) return error('Selecciona una obra primero');
  if (!estado.ia) return dialogoSinIA();

  const historial = [];
  const chat = el('div', { class: 'chat' });
  const entrada = el('input', { type: 'text', placeholder: 'Pregunta lo que necesites…', autocomplete: 'off' });

  const sugerencias = el('div', { class: 'chat-sug' }, SUGERENCIAS.map((s) =>
    el('button', { txt: s, onClick: () => { entrada.value = s; enviar(); } })));

  const cuerpo = el('div', {}, [
    sugerencias,
    chat,
    el('form', {
      class: 'chat-entrada',
      onSubmit: (e) => { e.preventDefault(); enviar(); },
    }, [entrada, el('button', { class: 'btn btn-pri', type: 'submit', txt: '➤' })]),
  ]);

  const m = modal({ titulo: `✨ Asistente · ${estado.obra?.nombre || ''}`, cuerpo, acciones: [{ texto: 'Cerrar' }] });

  async function enviar() {
    const texto = entrada.value.trim();
    if (!texto) return;
    entrada.value = '';
    sugerencias.style.display = 'none';
    chat.appendChild(el('div', { class: 'chat-msg chat-yo', txt: texto }));
    const pensando = el('div', { class: 'chat-msg chat-ia' }, [el('span', { class: 'girando', txt: '⏳' })]);
    chat.appendChild(pensando);
    chat.scrollTop = chat.scrollHeight;
    m.cuerpo.scrollTop = m.cuerpo.scrollHeight;

    try {
      const r = await api.preguntarIA(estado.obraId, texto, historial);
      pensando.remove();
      chat.appendChild(el('div', { class: 'chat-msg chat-ia', txt: r.respuesta }));
      historial.push({ role: 'user', content: texto }, { role: 'assistant', content: r.respuesta });
      if (historial.length > 12) historial.splice(0, 2);
    } catch (e) {
      pensando.remove();
      chat.appendChild(el('div', { class: 'chat-msg chat-ia', estilo: { color: 'var(--mal)' }, txt: `⚠️ ${e.message}` }));
    }
    m.cuerpo.scrollTop = m.cuerpo.scrollHeight;
  }

  setTimeout(() => entrada.focus(), 200);
}

// ═══════════════════════════════════════════════════════ sin clave
export function dialogoSinIA() {
  modal({
    titulo: '✨ Inteligencia artificial',
    cuerpo: el('div', {}, [
      el('div', { class: 'aviso-caja info' },
        'Las funciones de IA necesitan una clave de API de Anthropic. El resto de la aplicación funciona sin ella.'),
      el('p', { txt: 'Con la IA activada puedes:' }),
      el('ul', { estilo: { paddingLeft: '20px', lineHeight: '1.9', fontSize: '14px' } }, [
        el('li', { txt: '📷 Fotografiar la etiqueta de un equipo y darlo de alta solo (marca, modelo, nº de serie, MAC).' }),
        el('li', { txt: '📋 Fotografiar un albarán y cargar el material recibido en el almacén.' }),
        el('li', { txt: '✨ Preguntar por el estado de la obra en lenguaje natural.' }),
        el('li', { txt: '✍️ Redactar actas, correos de seguimiento e informes.' }),
      ]),
      el('p', { class: 'kpi-pie' },
        'Consigue tu clave en console.anthropic.com y pégala en Ajustes. Se guarda solo en tu equipo.'),
    ]),
    acciones: [
      { texto: 'Ahora no' },
      { texto: 'Ir a Ajustes', clase: 'btn-pri', accion: () => { window.obrasec.irA('ajustes'); } },
    ],
  });
}
