// Ajustes, plantillas de informe, importación de Excel y copias de seguridad.

import { api } from './api.js';
import { estado } from './estado.js';
import {
  el, $, limpiar, modal, confirmar, exito, error, info, cargando, descargar, fecha, pedirTexto,
} from './ui.js';

export async function vistaAjustes(host) {
  limpiar(host).appendChild(cargando());
  const [ajustes, plantillas] = await Promise.all([api.ajustes(), api.plantillas()]);
  limpiar(host);

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [el('h1', { txt: '⚙️ Ajustes' }), el('div', { class: 'sub', txt: `ObraSec ${estado.meta.version}` })]),
  ]));

  // ── Inteligencia artificial ─────────────────────────────────────────
  const claveInput = el('input', {
    type: 'password', placeholder: ajustes.ia_configurada ? ajustes.ia_clave_parcial || '••••••••' : 'sk-ant-…',
    autocomplete: 'off',
  });
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', { txt: '✨ Inteligencia artificial' }),
    el('div', {
      class: `aviso-caja ${ajustes.ia_configurada ? 'ok' : 'aviso'}`,
      txt: ajustes.ia_configurada
        ? 'Activada. Puedes escanear etiquetas, leer albaranes y usar el asistente.'
        : 'Sin configurar. La app funciona igual, pero sin escáner de etiquetas ni asistente.',
    }),
    el('div', { class: 'campo' }, [
      el('label', { txt: 'Clave de API de Anthropic' }),
      claveInput,
      el('div', { class: 'ayuda' }, [
        'Se obtiene en ',
        el('a', { href: 'https://console.anthropic.com/settings/keys', target: '_blank', rel: 'noopener', txt: 'console.anthropic.com' }),
        '. Se guarda cifrada en tu propio equipo y nunca sale de él salvo para hablar con la API.',
      ]),
    ]),
    el('div', { estilo: { display: 'flex', gap: '8px' } }, [
      el('button', {
        class: 'btn btn-pri', txt: 'Guardar clave',
        onClick: async (e) => {
          const v = claveInput.value.trim();
          if (!v) return error('Pega la clave primero');
          if (!v.startsWith('sk-ant-')) {
            const seguir = await confirmar('La clave no empieza por «sk-ant-». ¿Guardarla de todos modos?', { peligro: false, textoOk: 'Guardar' });
            if (!seguir) return;
          }
          await api.guardarAjustes({ anthropic_api_key: v });
          estado.ia = true;
          exito('Clave guardada. Ya puedes escanear etiquetas.');
          vistaAjustes(host);
        },
      }),
      ajustes.ia_configurada ? el('button', {
        class: 'btn', txt: 'Quitar clave',
        onClick: async () => {
          if (!await confirmar('¿Eliminar la clave de API guardada?')) return;
          await api.guardarAjustes({ anthropic_api_key: null });
          estado.ia = false;
          exito('Clave eliminada');
          vistaAjustes(host);
        },
      }) : null,
    ]),
  ]));

  // ── Plantillas de informe ───────────────────────────────────────────
  const listaPlantillas = el('div');
  const pintarPlantillas = (arr) => {
    limpiar(listaPlantillas);
    if (!arr.length) {
      listaPlantillas.appendChild(el('p', { class: 'kpi-pie', txt: 'Todavía no has subido ninguna plantilla. Se usará el informe estándar.' }));
      return;
    }
    for (const p of arr) {
      listaPlantillas.appendChild(el('div', {
        class: 'ficha', estilo: { display: 'flex', alignItems: 'center', gap: '10px' },
      }, [
        el('span', { txt: '📄', estilo: { fontSize: '22px' } }),
        el('div', { estilo: { flex: '1', minWidth: '0' } }, [
          el('div', { class: 'ficha-tit', txt: p.nombre }),
          el('small', { class: 'kpi-pie', txt: `Subida el ${fecha(p.creado)}` }),
        ]),
        el('button', {
          class: 'btn btn-peq', txt: '▶',
          title: 'Generar informe con esta plantilla para la obra activa',
          onClick: () => {
            if (!estado.obraId) return error('Selecciona una obra primero');
            descargar(`/api/informes/${estado.obraId}?plantilla=${p.id}`);
            info('Generando…');
          },
        }),
        el('button', {
          class: 'btn btn-peq', txt: '🗑',
          onClick: async () => {
            if (!await confirmar(`¿Eliminar la plantilla «${p.nombre}»?`)) return;
            await api.borrarPlantilla(p.id);
            pintarPlantillas(await api.plantillas());
            exito('Plantilla eliminada');
          },
        }),
      ]));
    }
  };
  pintarPlantillas(plantillas);

  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', { txt: '📄 Plantillas de informe' }),
    el('div', { class: 'aviso-caja info' },
      'Sube tus documentos de Word con tu membrete. Donde quieras que aparezca un dato, escribe su marcador entre llaves dobles.'),
    listaPlantillas,
    el('div', { estilo: { display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' } }, [
      el('button', {
        class: 'btn btn-pri', txt: '📤 Subir plantilla .docx',
        onClick: () => subirPlantilla(async () => pintarPlantillas(await api.plantillas())),
      }),
      el('button', { class: 'btn', txt: '❔ Ver marcadores disponibles', onClick: dialogoMarcadores }),
    ]),
  ]));

  // ── Importar desde Excel ────────────────────────────────────────────
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', { txt: '📥 Importar desde Excel' }),
    el('p', { class: 'kpi-pie', estilo: { marginTop: '0' } },
      'Carga tus libros «Control de Obra» actuales. Se reconocen las hojas de tareas, materiales, dispositivos, personal, subcontratas, maquinaria, incidencias, documentos, planos y ofertas.'),
    el('button', { class: 'btn btn-pri', txt: '📥 Elegir archivo Excel', onClick: dialogoImportar }),
  ]));

  // ── Copias de seguridad ─────────────────────────────────────────────
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', { txt: '💾 Copia de seguridad' }),
    el('p', { class: 'kpi-pie', estilo: { marginTop: '0' } },
      `Todos tus datos están en: ${ajustes.carpeta_datos}`),
    el('div', { class: 'aviso-caja aviso' },
      'Descarga una copia cada semana y guárdala fuera del ordenador. Una obra perdida no se recupera con buenas intenciones.'),
    el('div', { estilo: { display: 'flex', gap: '8px', flexWrap: 'wrap' } }, [
      el('button', { class: 'btn btn-pri', txt: '⬇ Descargar copia', onClick: () => { descargar('/api/backup'); info('Preparando la copia…'); } }),
      el('button', { class: 'btn', txt: '⬆ Restaurar copia', onClick: dialogoRestaurar }),
    ]),
  ]));

  // ── Seguridad ───────────────────────────────────────────────────────
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', { txt: '🔒 Seguridad' }),
    el('div', {
      class: `aviso-caja ${ajustes.requiere_password ? 'ok' : 'aviso'}`,
      txt: ajustes.requiere_password
        ? 'Acceso protegido con contraseña.'
        : 'Sin contraseña. Correcto si solo usas la app en este ordenador; imprescindible ponerla si la publicas en internet.',
    }),
    el('div', { estilo: { display: 'flex', gap: '8px', flexWrap: 'wrap' } }, [
      el('button', {
        class: 'btn btn-pri', txt: ajustes.requiere_password ? 'Cambiar contraseña' : 'Poner contraseña',
        onClick: async () => {
          const p = await pedirTexto({
            titulo: 'Contraseña de acceso', etiqueta: 'Nueva contraseña', tipo: 'password',
            ayuda: 'Mínimo 6 caracteres. Se cerrarán todas las sesiones abiertas.',
          });
          if (!p) return;
          try {
            await api.cambiarPassword(p);
            exito('Contraseña actualizada');
            vistaAjustes(host);
          } catch (e) { error(e.message); }
        },
      }),
      ajustes.requiere_password ? el('button', {
        class: 'btn', txt: 'Quitar contraseña',
        onClick: async () => {
          if (!await confirmar('¿Quitar la contraseña? Cualquiera con acceso a esta dirección podrá ver tus obras.')) return;
          await api.cambiarPassword('');
          exito('Contraseña eliminada');
          vistaAjustes(host);
        },
      }) : null,
      el('button', {
        class: 'btn', txt: 'Cerrar sesión',
        onClick: async () => { await api.logout(); location.reload(); },
      }),
    ]),
  ]));

  // ── Registro de actividad ───────────────────────────────────────────
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', { txt: '📜 Actividad reciente' }),
    el('button', {
      class: 'btn btn-peq', txt: 'Ver registro',
      onClick: async () => {
        const filas = await api.log(estado.obraId);
        modal({
          titulo: 'Registro de actividad',
          cuerpo: el('div', { class: 'tabla-caja' }, [
            el('table', {}, [
              el('thead', {}, [el('tr', {}, ['Fecha', 'Acción', 'Módulo'].map((h) => el('th', { txt: h })))]),
              el('tbody', {}, filas.slice(0, 200).map((l) => el('tr', {}, [
                el('td', { txt: new Date(l.fecha).toLocaleString('es-ES') }),
                el('td', { txt: l.accion }),
                el('td', { txt: l.entidad || '' }),
              ]))),
            ]),
          ]),
          acciones: [{ texto: 'Cerrar' }],
        });
      },
    }),
  ]));
}

// ══════════════════════════════════════════════════════════ plantillas
function subirPlantilla(alTerminar) {
  const entrada = $('#entrada-archivo');
  entrada.accept = '.docx,.dotx';
  entrada.value = '';
  const alCambiar = async () => {
    entrada.removeEventListener('change', alCambiar);
    const archivo = entrada.files[0];
    if (!archivo) return;
    const nombre = await pedirTexto({
      titulo: 'Nombre de la plantilla',
      etiqueta: '¿Cómo la llamamos?',
      valor: archivo.name.replace(/\.[^.]+$/, ''),
      ayuda: 'Por ejemplo: «Acta de recepción», «Informe semanal Telefónica».',
    });
    if (nombre === null) return;
    const fd = new FormData();
    fd.append('archivo', archivo);
    fd.append('nombre', nombre || archivo.name);
    try {
      await api.subir('/api/plantillas', fd);
      exito('Plantilla subida');
      if (alTerminar) await alTerminar();
    } catch (e) { error(e.message); }
  };
  entrada.addEventListener('change', alCambiar);
  entrada.click();
}

async function dialogoMarcadores() {
  const campos = await api.camposPlantilla();
  const cuerpo = el('div', {}, [
    el('div', { class: 'aviso-caja info' },
      'Escribe el marcador tal cual en tu documento de Word. Ejemplo: Obra: {{ obra.nombre }} — Avance: {{ kpi.avance }} %'),
    el('div', { class: 'aviso-caja aviso' },
      'Para listar tablas usa un bucle: {% for x in dispositivos %} … {{ x.etiqueta }} … {% endfor %}. En una tabla de Word, pon la apertura del bucle en la primera celda de la fila y el cierre en la última.'),
  ]);
  for (const [grupo, lista] of Object.entries(campos)) {
    const det = el('details', { estilo: { marginBottom: '8px' } }, [
      el('summary', { txt: grupo, estilo: { cursor: 'pointer', fontWeight: '600', padding: '6px 0' } }),
      el('div', { class: 'leido', txt: lista.map((c) => (c.includes('{%') ? c : `{{ ${c} }}`)).join('\n') }),
    ]);
    cuerpo.appendChild(det);
  }
  modal({ titulo: 'Marcadores disponibles', cuerpo, acciones: [{ texto: 'Cerrar' }] });
}

// ══════════════════════════════════════════════════════════ importar
export function dialogoImportar() {
  const entrada = $('#entrada-archivo');
  entrada.accept = '.xlsx,.xlsm';
  entrada.value = '';
  const alCambiar = async () => {
    entrada.removeEventListener('change', alCambiar);
    const archivo = entrada.files[0];
    if (!archivo) return;

    const cuerpo = el('div', {}, [cargando('Analizando el libro…')]);
    const m = modal({ titulo: '📥 Importar Excel', cuerpo, acciones: [{ texto: 'Cancelar' }] });

    let informe;
    try {
      const fd = new FormData();
      fd.append('archivo', archivo);
      informe = await api.subir('/api/import/analizar', fd);
    } catch (e) {
      limpiar(cuerpo).appendChild(el('div', { class: 'aviso-caja mal', txt: e.message }));
      return;
    }

    const reconocidas = informe.hojas.filter((h) => h.destino && h.filas > 0);
    limpiar(cuerpo);

    if (!reconocidas.length) {
      cuerpo.appendChild(el('div', { class: 'aviso-caja aviso' },
        'No se ha reconocido ninguna hoja con datos. Comprueba que las hojas se llamen Tareas, Materiales, Dispositivos, Personal, Subcontratas, Maquinaria, Incidencias, Documentos, Planos u Ofertas.'));
      return;
    }

    // Destino: obra existente o nueva
    const selObra = el('select', {}, [
      el('option', { value: '__nueva__', txt: '➕ Crear una obra nueva con estos datos' }),
      ...estado.obras.map((o) => el('option', {
        value: o.id, txt: o.nombre, selected: String(o.id) === String(estado.obraId),
      })),
    ]);

    const marcas = [];
    cuerpo.appendChild(el('div', { class: 'campo' }, [
      el('label', { txt: '¿A qué obra se importan los datos?' }),
      selObra,
    ]));
    cuerpo.appendChild(el('h2', { txt: 'Hojas detectadas', estilo: { fontSize: '14px', margin: '16px 0 8px' } }));

    for (const h of reconocidas) {
      const chk = el('input', { type: 'checkbox', checked: true });
      marcas.push({ chk, hoja: h.hoja });
      cuerpo.appendChild(el('label', {
        class: 'ficha', estilo: { display: 'flex', gap: '10px', alignItems: 'flex-start', cursor: 'pointer' },
      }, [
        chk,
        el('div', { estilo: { flex: '1' } }, [
          el('div', { class: 'ficha-tit', txt: `${h.hoja} → ${h.entidad}` }),
          el('div', { class: 'ficha-datos' }, [
            el('span', {}, [el('b', { txt: String(h.filas) }), ' filas']),
            el('span', {}, [el('b', { txt: String(h.columnas.length) }), ' columnas reconocidas']),
          ]),
          h.ignoradas?.length
            ? el('small', { class: 'kpi-pie', txt: `Se ignoran: ${h.ignoradas.slice(0, 6).join(', ')}` })
            : null,
        ]),
      ]));
    }

    const pie = m.caja.querySelector('.modal-pie');
    limpiar(pie);
    pie.appendChild(el('button', { class: 'btn', txt: 'Cancelar', onClick: () => m.cerrar() }));
    pie.appendChild(el('button', {
      class: 'btn btn-pri', txt: 'Importar',
      onClick: async (ev) => {
        const boton = ev.currentTarget;
        boton.disabled = true;
        boton.textContent = 'Importando…';
        try {
          let obraId = selObra.value;
          if (obraId === '__nueva__') {
            const ficha = informe.ficha_obra || {};
            const nueva = await api.crear('obras', {
              nombre: ficha.nombre || archivo.name.replace(/\.[^.]+$/, ''),
              cliente: ficha.cliente || 'Telefónica Soluciones',
              estado: ficha.estado || 'En curso',
              ...ficha,
            });
            obraId = nueva.id;
            await window.obrasec.recargarObras();
          }
          const hojas = marcas.filter((x) => x.chk.checked).map((x) => x.hoja);
          const r = await api.importarEjecutar(informe.archivo, Number(obraId), hojas);
          m.cerrar();
          const detalle = Object.entries(r.importado).map(([k, v]) => `${v} ${k.toLowerCase()}`).join(', ');
          exito(detalle ? `Importado: ${detalle}` : 'No se importó ninguna fila');
          await window.obrasec.seleccionarObra(Number(obraId));
        } catch (e) {
          error(e.message);
          boton.disabled = false;
          boton.textContent = 'Importar';
        }
      },
    }));
  };
  entrada.addEventListener('change', alCambiar);
  entrada.click();
}

// ═════════════════════════════════════════════════════════ restaurar
function dialogoRestaurar() {
  const entrada = $('#entrada-archivo');
  entrada.accept = '.zip';
  entrada.value = '';
  const alCambiar = async () => {
    entrada.removeEventListener('change', alCambiar);
    const archivo = entrada.files[0];
    if (!archivo) return;
    const ok = await confirmar(
      'Restaurar sustituye TODOS los datos actuales por los de la copia. Se guarda antes un respaldo automático. ¿Continuar?',
      { titulo: 'Restaurar copia de seguridad', textoOk: 'Sí, restaurar' }
    );
    if (!ok) return;
    try {
      const fd = new FormData();
      fd.append('archivo', archivo);
      await api.subir('/api/restore', fd);
      exito('Copia restaurada. Recargando…');
      setTimeout(() => location.reload(), 1200);
    } catch (e) { error(e.message); }
  };
  entrada.addEventListener('change', alCambiar);
  entrada.click();
}
