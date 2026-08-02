// Vistas de la aplicación: cuadro de mando, listados, ficha de detalle y Gantt.

import { api } from './api.js';
import { estado } from './estado.js';
import {
  el, $, $$, limpiar, eur, num, fecha, fechaCorta, relativa, diasHasta, claseEstado,
  etiqueta, kpi, barra, modal, confirmar, exito, error, info, vacio, cargando, descargar,
} from './ui.js';
import { editar, cargarRefs, textoRef } from './forms.js';

const ICONO_SEV = { critica: '🔴', alta: '🟠', media: '🔵', info: 'ℹ️' };

// ═══════════════════════════════════════════════════════ cuadro de mando
export async function vistaPanel(host) {
  if (!estado.obraId) return vistaMultiObra(host);

  limpiar(host).appendChild(cargando('Calculando indicadores…'));
  let r;
  try {
    r = await api.resumen(estado.obraId);
  } catch (e) {
    return limpiar(host).appendChild(vacio({
      icono: '⚠️', titulo: 'No se pudo cargar la obra', texto: e.message,
    }));
  }
  estado.resumen = r;
  limpiar(host);

  const { tareas, dispositivos: disp, economico: eco, plazo, otros, alertas } = r;

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [
      el('h1', { txt: 'Cuadro de mando' }),
      el('div', { class: 'sub', txt: `${r.obra.nombre || ''} · ${r.obra.estado || ''}` }),
    ]),
    el('button', {
      class: 'btn btn-peq', txt: '📊 Excel',
      onClick: () => descargar(`/api/export/obra/${estado.obraId}`),
    }),
    el('button', {
      class: 'btn btn-peq btn-pri', txt: '📄 Informe',
      onClick: () => dialogoInforme(),
    }),
  ]));

  // ── Alertas: lo primero que debe ver un jefe de obra ─────────────────
  if (alertas.length) {
    const criticas = alertas.filter((a) => a.severidad === 'critica').length;
    const caja = el('div', { class: 'tarjeta' }, [
      el('h2', {}, [
        `Puntos de atención `,
        el('span', { class: 'sub', txt: `${alertas.length} avisos${criticas ? ` · ${criticas} críticos` : ''}` }),
      ]),
    ]);
    const mostrar = alertas.slice(0, 6);
    for (const a of mostrar) caja.appendChild(fichaAlerta(a));
    if (alertas.length > 6) {
      caja.appendChild(el('button', {
        class: 'btn btn-peq btn-ancho', txt: `Ver los ${alertas.length - 6} avisos restantes`,
        onClick: () => modal({
          titulo: 'Todos los puntos de atención',
          cuerpo: el('div', {}, alertas.map(fichaAlerta)),
          acciones: [{ texto: 'Cerrar' }],
        }),
      }));
    }
    host.appendChild(caja);
  } else {
    host.appendChild(el('div', { class: 'tarjeta' }, [
      el('div', { class: 'aviso-caja ok', txt: '✅ Sin puntos de atención. Todo en orden a día de hoy.' }),
    ]));
  }

  // ── Indicadores ──────────────────────────────────────────────────────
  const desv = plazo.desviacion;
  host.appendChild(el('div', { class: 'rejilla rejilla-kpi', estilo: { marginBottom: '14px' } }, [
    kpi({
      etiqueta: 'Avance global', valor: `${tareas.avance}%`, pct: tareas.avance,
      pie: `${tareas.completadas} de ${tareas.total} tareas`,
      clase: tareas.avance >= 80 ? 'ok' : tareas.avance < 30 ? '' : 'aviso',
      alPulsar: () => irA('tareas'),
    }),
    kpi({
      etiqueta: 'Plazo', valor: plazo.dias_restantes === null ? '—' : `${plazo.dias_restantes} d`,
      pie: plazo.consumido_pct !== null
        ? `${plazo.consumido_pct}% de plazo consumido${desv > 5 ? ` · ${desv} pts de desvío` : ''}`
        : 'Sin fechas definidas',
      clase: plazo.dias_restantes === null ? '' : plazo.dias_restantes < 0 ? 'mal'
        : plazo.dias_restantes < 15 ? 'aviso' : 'ok',
      pct: plazo.consumido_pct ?? undefined,
    }),
    kpi({
      etiqueta: 'Equipos instalados', valor: `${disp.instalados}/${disp.total}`,
      pct: disp.pct_instalado, pie: `${disp.probados} probados · ${disp.unidades} uds.`,
      clase: disp.pct_instalado >= 90 ? 'ok' : '',
      alPulsar: () => irA('dispositivos'),
    }),
    kpi({
      etiqueta: 'Margen', valor: eco.ingresos ? `${eco.margen_pct}%` : '—',
      pie: eco.ingresos ? eur(eco.margen) : 'Falta importe de contrato',
      clase: !eco.ingresos ? '' : eco.margen_pct < 0 ? 'mal' : eco.margen_pct < 10 ? 'aviso' : 'ok',
      alPulsar: () => irA('economico'),
    }),
    kpi({
      etiqueta: 'Tareas con retraso', valor: tareas.retrasadas,
      pie: tareas.bloqueadas ? `${tareas.bloqueadas} bloqueadas` : 'Ninguna bloqueada',
      clase: tareas.retrasadas ? 'mal' : 'ok',
      alPulsar: () => irA('tareas'),
    }),
    kpi({
      etiqueta: 'Incidencias abiertas', valor: otros.incidencias_abiertas,
      clase: otros.incidencias_abiertas ? 'aviso' : 'ok',
      alPulsar: () => irA('incidencias'),
    }),
    kpi({
      etiqueta: 'Personal con acceso', valor: `${otros.personal_con_acceso}/${otros.personal}`,
      clase: otros.personal && otros.personal_con_acceso < otros.personal ? 'aviso' : 'ok',
      alPulsar: () => irA('personal'),
    }),
    kpi({
      etiqueta: 'Docs. pendientes', valor: otros.docs_pendientes,
      clase: otros.docs_pendientes ? 'aviso' : 'ok',
      alPulsar: () => irA('documentos'),
    }),
  ]));

  // ── Económico ────────────────────────────────────────────────────────
  host.appendChild(el('div', { class: 'rejilla rejilla-2' }, [
    el('div', { class: 'tarjeta' }, [
      el('h2', { txt: 'Situación económica' }),
      tablaPares([
        ['Importe de contrato', eur(eco.contrato)],
        ['Ampliaciones aprobadas', eur(eco.ampliaciones)],
        ['Ingreso total', eur(eco.ingresos)],
        ['Coste incurrido', eur(eco.coste_total)],
        ['Margen bruto', eur(eco.margen)],
        ['Certificado', eur(eco.certificado)],
        ['Pendiente de cobro', eur(eco.pendiente_cobro)],
      ]),
      el('h2', { txt: 'Desglose de coste', estilo: { marginTop: '16px' } }),
      miniBarras(eco.desglose, eco.coste_total, (v) => eur(v)),
    ]),
    el('div', { class: 'tarjeta' }, [
      el('h2', { txt: 'Tareas por estado' }),
      miniBarras(tareas.por_estado, tareas.total),
      el('h2', { txt: 'Equipos por estado', estilo: { marginTop: '16px' } }),
      miniBarras(disp.por_estado, disp.total),
      el('h2', { txt: 'Equipos por categoría', estilo: { marginTop: '16px' } }),
      miniBarras(disp.por_categoria, disp.total),
    ]),
  ]));
}

function fichaAlerta(a) {
  return el('div', {
    class: `alerta ${a.severidad}`,
    onClick: () => a.modulo && irA(a.modulo),
  }, [
    el('div', { class: 'alerta-icono', txt: ICONO_SEV[a.severidad] || '•' }),
    el('div', { estilo: { flex: '1', minWidth: '0' } }, [
      el('strong', { txt: a.titulo }),
      a.detalle ? el('p', { txt: a.detalle }) : null,
    ]),
  ]);
}

function tablaPares(pares) {
  return el('dl', { class: 'lista-def' }, pares.flatMap(([k, v]) => [
    el('dt', { txt: k }),
    el('dd', { txt: String(v) }),
  ]));
}

function miniBarras(mapa, total, formato) {
  const entradas = Object.entries(mapa || {}).filter(([, v]) => v);
  if (!entradas.length) return el('p', { class: 'kpi-pie', txt: 'Sin datos todavía.' });
  const max = Math.max(...entradas.map(([, v]) => v), 1);
  return el('div', { class: 'mini-barras' }, entradas.map(([k, v]) =>
    el('div', { class: 'mini-barra' }, [
      el('span', { class: 'etq-txt', txt: k, title: k }),
      el('div', { class: 'pista' }, [
        el('i', {
          estilo: {
            width: `${(v / max) * 100}%`,
            background: `var(--${claseEstado(k) === 'ok' ? 'ok' : claseEstado(k) === 'mal' ? 'mal' : claseEstado(k) === 'aviso' ? 'aviso' : 'pri'})`,
          },
        }),
      ]),
      el('span', { class: 'n', txt: formato ? formato(v) : num(v) }),
    ])
  ));
}

// ═══════════════════════════════════════════════════ panel multi-obra
export async function vistaMultiObra(host) {
  limpiar(host).appendChild(cargando('Cargando obras…'));
  const filas = await api.panel();
  limpiar(host);

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [
      el('h1', { txt: 'Mis obras' }),
      el('div', { class: 'sub', txt: `${filas.length} obras activas` }),
    ]),
    el('button', {
      class: 'btn btn-pri', txt: '+ Nueva obra',
      onClick: () => editar('obras', null, { alGuardar: () => window.obrasec.recargarObras(true) }),
    }),
  ]));

  if (!filas.length) {
    host.appendChild(vacio({
      icono: '🏗️', titulo: 'Todavía no hay ninguna obra',
      texto: 'Crea tu primera obra o importa uno de tus Excel de control para empezar con los datos que ya tienes.',
      accion: {
        texto: 'Crear primera obra',
        alPulsar: () => editar('obras', null, { alGuardar: () => window.obrasec.recargarObras(true) }),
      },
    }));
    host.appendChild(el('div', { estilo: { textAlign: 'center' } }, [
      el('button', { class: 'btn', txt: '📥 Importar desde Excel', onClick: () => irA('importar') }),
    ]));
    return;
  }

  host.appendChild(el('div', { class: 'rejilla rejilla-2' }, filas.map((f) => {
    const o = f.obra;
    return el('div', {
      class: 'tarjeta', estilo: { cursor: 'pointer', marginBottom: '0' },
      onClick: () => window.obrasec.seleccionarObra(o.id),
    }, [
      el('div', { estilo: { display: 'flex', gap: '8px', alignItems: 'flex-start', marginBottom: '8px' } }, [
        el('div', { estilo: { flex: '1', minWidth: '0' } }, [
          el('strong', { txt: o.nombre, estilo: { fontSize: '15px', display: 'block' } }),
          el('small', {
            class: 'kpi-pie',
            txt: [o.codigo, o.cliente, o.poblacion].filter(Boolean).join(' · '),
          }),
        ]),
        etiqueta(o.estado),
      ]),
      barra(f.avance, f.avance >= 80 ? 'ok' : ''),
      el('div', {
        class: 'ficha-datos',
        estilo: { marginTop: '9px' },
      }, [
        el('span', {}, [el('b', { txt: `${f.avance}%` }), ' avance']),
        el('span', {}, [el('b', { txt: `${f.instalados}/${f.dispositivos}` }), ' equipos']),
        f.dias_restantes !== null
          ? el('span', {}, [el('b', { txt: `${f.dias_restantes}` }), ' días'])
          : null,
        f.criticas
          ? el('span', { estilo: { color: 'var(--mal)', fontWeight: '700' }, txt: `🔴 ${f.criticas} críticos` })
          : f.alertas
            ? el('span', { estilo: { color: 'var(--aviso)' }, txt: `${f.alertas} avisos` })
            : el('span', { estilo: { color: 'var(--ok)' }, txt: '✅ Sin avisos' }),
      ]),
    ]);
  })));
}

// ═══════════════════════════════════════════════════════════ listados
export async function vistaEntidad(host, entidad) {
  const ent = estado.meta.entidades[entidad];
  if (ent.per_obra && !estado.obraId) {
    return limpiar(host).appendChild(vacio({
      icono: '🏗️', titulo: 'Selecciona una obra',
      texto: 'Este módulo muestra los datos de una obra concreta.',
      accion: { texto: 'Ver mis obras', alPulsar: () => irA('panel') },
    }));
  }

  limpiar(host).appendChild(cargando());
  await cargarRefs(entidad);
  let filas = await api.listar(entidad, ent.per_obra ? estado.obraId : null);
  limpiar(host);

  const columnas = ent.fields.filter((f) => f.list);
  const campoEstado = ent.fields.find((f) => f.name === 'estado');

  const contador = el('div', { class: 'sub' });
  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [
      el('h1', {}, [`${ent.icon} `, ent.plural]),
      contador,
    ]),
    el('button', {
      class: 'btn btn-peq', txt: '📊 Excel',
      onClick: () => descargar(`/api/export/${entidad}${estado.obraId ? `?obra=${estado.obraId}` : ''}`),
    }),
    entidad === 'dispositivos' ? el('button', {
      class: 'btn btn-peq', txt: '📷 Escanear',
      onClick: () => window.obrasec.escanearEtiqueta(),
    }) : null,
    el('button', {
      class: 'btn btn-pri', txt: `+ Nuevo`,
      onClick: () => nuevoRegistro(entidad, host),
    }),
  ]));

  // Filtros
  const buscador = el('input', { type: 'search', placeholder: `Buscar en ${ent.plural.toLowerCase()}…` });
  const filtroEstado = campoEstado ? el('select', {}, [
    el('option', { value: '', txt: 'Todos los estados' }),
    ...(campoEstado.options || estado.meta.catalogos[campoEstado.cat] || [])
      .map((o) => el('option', { value: o, txt: o })),
  ]) : null;
  host.appendChild(el('div', { class: 'filtros' }, [buscador, filtroEstado].filter(Boolean)));

  const contenedor = el('div');
  host.appendChild(contenedor);

  const pintar = () => {
    const q = buscador.value.toLowerCase().trim();
    const est = filtroEstado?.value || '';
    const visibles = filas.filter((f) => {
      if (est && f.estado !== est) return false;
      if (!q) return true;
      return Object.values(f).some((v) => String(v ?? '').toLowerCase().includes(q));
    });
    contador.textContent = visibles.length === filas.length
      ? `${filas.length} registros`
      : `${visibles.length} de ${filas.length} registros`;

    limpiar(contenedor);
    if (!visibles.length) {
      contenedor.appendChild(vacio({
        icono: ent.icon,
        titulo: filas.length ? 'Sin resultados' : `Todavía no hay ${ent.plural.toLowerCase()}`,
        texto: filas.length ? 'Prueba con otro texto o quita el filtro de estado.'
          : `Pulsa «+ Nuevo» para añadir el primer registro.`,
        accion: filas.length ? null
          : { texto: `+ Nueva ${ent.label.toLowerCase()}`, alPulsar: () => nuevoRegistro(entidad, host) },
      }));
      return;
    }

    const esMovil = window.innerWidth < 861;
    contenedor.appendChild(esMovil
      ? listaFichas(entidad, visibles, columnas, host)
      : listaTabla(entidad, visibles, columnas, host));
  };

  buscador.addEventListener('input', pintar);
  filtroEstado?.addEventListener('change', pintar);
  pintar();

  host.appendChild(el('button', {
    class: 'flotante', txt: '+', 'aria-label': 'Nuevo',
    onClick: () => nuevoRegistro(entidad, host),
  }));
}

function nuevoRegistro(entidad, host) {
  const iniciales = {};
  const ent = estado.meta.entidades[entidad];
  // Prerrellena la fecha de hoy en los campos de fecha obligatorios.
  for (const f of ent.fields) {
    if (f.type === 'date' && f.req) iniciales[f.name] = new Date().toISOString().slice(0, 10);
  }
  return editar(entidad, null, {
    valoresIniciales: iniciales,
    alGuardar: () => vistaEntidad(host, entidad),
  });
}

function valorCelda(campo, fila) {
  const v = fila[campo.name];
  if (v === null || v === undefined || v === '') return el('span', { estilo: { color: 'var(--texto-2)' }, txt: '—' });
  if (campo.type === 'ref') return el('span', { txt: textoRef(campo, v) });
  if (campo.type === 'bool') return el('span', { txt: v ? '✅' : '—' });
  if (campo.type === 'money') return el('span', { txt: eur(v) });
  if (campo.type === 'percent') return el('span', { txt: `${num(v, 0)}%` });
  if (campo.type === 'number') return el('span', { txt: num(v, 2) });
  if (campo.type === 'date') {
    const d = diasHasta(v);
    const vencida = d !== null && d < 0 && !['fecha_fin_real', 'fecha_cierre', 'fecha_inicio',
      'fecha_entrega', 'fecha_instalacion', 'fecha_recepcion', 'fecha_envio', 'fecha_compra',
      'fecha_alta', 'fecha_prueba', 'fecha_revision', 'fecha_entrada', 'fecha'].includes(campo.name);
    return el('span', {
      txt: fecha(v),
      estilo: vencida ? { color: 'var(--mal)', fontWeight: '600' } : {},
      title: relativa(v),
    });
  }
  if (campo.name === 'estado' || campo.name === 'gravedad' || campo.name === 'prioridad'
      || campo.name === 'seguro_rc' || campo.name === 'prl_ok') {
    return etiqueta(v);
  }
  return el('span', { txt: String(v) });
}

function listaTabla(entidad, filas, columnas, host) {
  const ent = estado.meta.entidades[entidad];
  return el('div', { class: 'tabla-caja' }, [
    el('table', {}, [
      el('thead', {}, [el('tr', {}, columnas.map((c) => el('th', { txt: c.label })))]),
      el('tbody', {}, filas.map((f) => el('tr', {
        onClick: () => abrirDetalle(entidad, f.id, host),
      }, columnas.map((c) => el('td', {
        class: ['money', 'number', 'percent', 'int'].includes(c.type) ? 'num' : '',
      }, [valorCelda(c, f)]))))),
    ]),
  ]);
}

function listaFichas(entidad, filas, columnas, host) {
  const ent = estado.meta.entidades[entidad];
  const principal = columnas[0] || ent.fields[0];
  const resto = columnas.slice(1, 5);
  return el('div', { class: 'fichas' }, filas.map((f) => el('div', {
    class: 'ficha', onClick: () => abrirDetalle(entidad, f.id, host),
  }, [
    el('div', { class: 'ficha-cab' }, [
      el('div', { class: 'ficha-tit', txt: f[principal.name] || `#${f.id}` }),
      f.estado ? etiqueta(f.estado) : null,
    ]),
    el('div', { class: 'ficha-datos' }, resto
      .filter((c) => c.name !== 'estado' && f[c.name] !== null && f[c.name] !== '')
      .map((c) => el('span', {}, [`${c.label}: `, el('b', {}, [valorCelda(c, f)])]))),
  ])));
}

// ═══════════════════════════════════════════════════════ ficha detalle
export async function abrirDetalle(entidad, id, host) {
  const ent = estado.meta.entidades[entidad];
  await cargarRefs(entidad);
  const reg = await api.obtener(entidad, id);

  const cuerpo = el('div');

  // Datos agrupados igual que el formulario.
  for (const grupo of ent.groups) {
    const campos = ent.fields.filter((f) => f.group === grupo
      && reg[f.name] !== null && reg[f.name] !== undefined && reg[f.name] !== '');
    if (!campos.length) continue;
    cuerpo.appendChild(el('h2', {
      txt: grupo,
      estilo: { fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.5px', color: 'var(--texto-2)', margin: '16px 0 8px' },
    }));
    cuerpo.appendChild(el('dl', { class: 'lista-def' }, campos.flatMap((c) => [
      el('dt', { txt: c.label }),
      el('dd', {}, [valorCelda(c, reg)]),
    ])));
  }

  // Adjuntos y fotos
  const zonaAdjuntos = el('div');
  cuerpo.appendChild(el('h2', {
    txt: 'Fotos y documentos',
    estilo: { fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.5px', color: 'var(--texto-2)', margin: '18px 0 8px' },
  }));
  cuerpo.appendChild(zonaAdjuntos);
  cuerpo.appendChild(el('div', { estilo: { display: 'flex', gap: '8px', marginTop: '10px' } }, [
    el('button', {
      class: 'btn btn-peq', txt: '📷 Añadir foto',
      onClick: () => window.obrasec.subirArchivo({ entidad, registroId: id, camara: true, alSubir: pintarAdjuntos }),
    }),
    el('button', {
      class: 'btn btn-peq', txt: '📎 Adjuntar archivo',
      onClick: () => window.obrasec.subirArchivo({ entidad, registroId: id, camara: false, alSubir: pintarAdjuntos }),
    }),
  ]));

  async function pintarAdjuntos() {
    const lista = await api.adjuntos(entidad, id);
    limpiar(zonaAdjuntos);
    if (!lista.length) {
      zonaAdjuntos.appendChild(el('p', { class: 'kpi-pie', txt: 'Sin fotos ni documentos adjuntos.' }));
      return;
    }
    zonaAdjuntos.appendChild(el('div', { class: 'galeria' }, lista.map((a) => {
      const url = `/api/adjuntos/${a.id}/archivo`;
      const esImagen = (a.mime || '').startsWith('image/');
      const nodo = esImagen
        ? el('img', { src: url, alt: a.nombre, loading: 'lazy' })
        : el('div', { class: 'doc', txt: '📄', title: a.nombre });
      nodo.addEventListener('click', () => modal({
        titulo: a.nombre,
        cuerpo: el('div', { estilo: { textAlign: 'center' } }, [
          esImagen
            ? el('img', { src: url, estilo: { maxWidth: '100%', borderRadius: '10px' } })
            : el('p', { txt: 'Vista previa no disponible para este tipo de archivo.' }),
          a.descripcion ? el('p', { class: 'kpi-pie', txt: a.descripcion }) : null,
        ]),
        acciones: [
          {
            texto: '🗑 Eliminar', clase: 'btn-mal',
            accion: async () => {
              if (!await confirmar('¿Eliminar este archivo?')) return false;
              await api.borrarAdjunto(a.id);
              await pintarAdjuntos();
              exito('Archivo eliminado');
            },
          },
          { texto: '⬇ Descargar', accion: () => { descargar(url); return false; }, cargando: false },
          { texto: 'Cerrar' },
        ],
      }));
      return nodo;
    })));
  }
  await pintarAdjuntos();

  const acciones = [
    { texto: 'Cerrar' },
    {
      texto: '⧉ Duplicar',
      accion: async () => {
        const veces = await import('./ui.js').then((m) => m.pedirTexto({
          titulo: 'Duplicar registro', etiqueta: '¿Cuántas copias?', valor: '1', tipo: 'number',
          ayuda: 'Si el nombre acaba en número, se numeran automáticamente (CAM-01 → CAM-02, CAM-03…).',
        }));
        if (!veces) return false;
        const r = await api.duplicar(entidad, id, Math.max(1, Math.min(200, parseInt(veces, 10) || 1)));
        exito(`${r.creados} copia(s) creada(s)`);
        if (host) await vistaEntidad(host, entidad);
      },
    },
    {
      texto: '✏️ Editar', clase: 'btn-pri',
      accion: async () => {
        await editar(entidad, reg, { alGuardar: () => host && vistaEntidad(host, entidad) });
      },
    },
  ];

  modal({ titulo: reg[ent.title_field] || `${ent.label} #${id}`, cuerpo, acciones });
}

// ═══════════════════════════════════════════════════════════════ Gantt
export async function vistaGantt(host) {
  if (!estado.obraId) {
    return limpiar(host).appendChild(vacio({ icono: '📅', titulo: 'Selecciona una obra' }));
  }
  limpiar(host).appendChild(cargando('Dibujando calendario…'));
  const g = await api.gantt(estado.obraId);
  limpiar(host);

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [
      el('h1', { txt: '📅 Calendario de obra' }),
      el('div', { class: 'sub', txt: `${g.tareas.length} tareas planificadas` }),
    ]),
    el('button', { class: 'btn btn-peq', txt: '+ Tarea', onClick: () => editar('tareas', null, { alGuardar: () => vistaGantt(host) }) }),
  ]));

  if (!g.tareas.length) {
    return host.appendChild(vacio({
      icono: '📅', titulo: 'Ninguna tarea con fechas',
      texto: 'Añade fechas de inicio y fin a las tareas para que aparezcan en el calendario.',
      accion: { texto: 'Ir a tareas', alPulsar: () => irA('tareas') },
    }));
  }

  const desde = new Date(g.desde);
  const hasta = new Date(g.hasta);
  const total = Math.max(1, Math.round((hasta - desde) / 86400000) + 1);
  const pctDe = (f) => ((new Date(f) - desde) / 86400000 / total) * 100;

  const leyenda = el('div', { class: 'ficha-datos', estilo: { marginBottom: '10px' } }, [
    ['Planificada', 'plan'], ['En curso', 'curso'], ['Completada', 'ok'],
    ['Retrasada', 'retraso'], ['Bloqueada', 'bloq'],
  ].map(([t, c]) => el('span', {}, [
    el('i', {
      estilo: {
        display: 'inline-block', width: '11px', height: '11px', borderRadius: '3px',
        marginRight: '5px', verticalAlign: 'middle',
        background: { plan: '#64748b', curso: 'var(--aviso)', ok: 'var(--ok)', retraso: 'var(--mal)', bloq: '#7c3aed' }[c],
      },
    }),
    t,
  ])));

  const pista = (contenido) => el('div', { class: 'gantt-pista' }, contenido);
  const filas = g.tareas.map((t) => {
    const izq = Math.max(0, pctDe(t.inicio));
    const ancho = Math.max(1.2, (t.dias / total) * 100);
    return el('div', { class: 'gantt-fila' }, [
      el('div', { class: 'gantt-nombre', txt: (t.hito ? '◆ ' : '') + t.tarea, title: t.tarea }),
      pista([
        el('div', {
          class: `gantt-barra ${t.color}`,
          estilo: { left: `${izq}%`, width: `${ancho}%` },
          title: `${t.tarea}\n${fecha(t.inicio)} → ${fecha(t.fin)}\n${t.estado} · ${t.avance}%`,
          onClick: () => abrirDetalle('tareas', t.id, host),
          txt: ancho > 12 ? `${t.avance}%` : '',
        }),
        el('div', { class: 'gantt-hoy', estilo: { left: `${pctDe(g.hoy)}%` } }),
      ]),
    ]);
  });

  // Cabecera de meses
  const meses = [];
  const cursor = new Date(desde.getFullYear(), desde.getMonth(), 1);
  while (cursor <= hasta) {
    const pct = pctDe(cursor.toISOString().slice(0, 10));
    if (pct >= 0) {
      meses.push(el('div', {
        class: 'gantt-mes', estilo: { left: `${pct}%` },
        txt: cursor.toLocaleDateString('es-ES', { month: 'short', year: '2-digit' }),
      }));
    }
    cursor.setMonth(cursor.getMonth() + 1);
  }

  host.appendChild(el('div', { class: 'tarjeta' }, [
    leyenda,
    el('div', { class: 'gantt' }, [
      el('div', { class: 'gantt-cab' }, [
        el('div', { class: 'gantt-nombre', txt: 'Tarea' }),
        pista(meses),
      ]),
      ...filas,
    ]),
  ]));
}

// ═════════════════════════════════════════════════════════ económico
export async function vistaEconomico(host) {
  if (!estado.obraId) return limpiar(host).appendChild(vacio({ icono: '💶', titulo: 'Selecciona una obra' }));
  limpiar(host).appendChild(cargando());
  const [r, partidas, stock] = await Promise.all([
    api.resumen(estado.obraId), api.listar('partidas', estado.obraId), api.stock(estado.obraId),
  ]);
  limpiar(host);
  const eco = r.economico;

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [el('h1', { txt: '💶 Económico' }), el('div', { class: 'sub', txt: r.obra.nombre })]),
    el('button', { class: 'btn btn-peq btn-pri', txt: '+ Partida', onClick: () => editar('partidas', null, { alGuardar: () => vistaEconomico(host) }) }),
  ]));

  host.appendChild(el('div', { class: 'rejilla rejilla-kpi', estilo: { marginBottom: '14px' } }, [
    kpi({ etiqueta: 'Ingreso total', valor: eur(eco.ingresos), pie: `Contrato ${eur(eco.contrato)} + ampliaciones` }),
    kpi({ etiqueta: 'Coste incurrido', valor: eur(eco.coste_total) }),
    kpi({
      etiqueta: 'Margen bruto', valor: eur(eco.margen), pie: `${eco.margen_pct}%`,
      clase: eco.margen < 0 ? 'mal' : eco.margen_pct < 10 ? 'aviso' : 'ok',
    }),
    kpi({
      etiqueta: 'Pendiente de cobro', valor: eur(eco.pendiente_cobro),
      pie: `Certificado ${eur(eco.certificado)}`,
      clase: eco.pendiente_cobro > 0 ? 'aviso' : 'ok',
    }),
  ]));

  // Presupuesto vs real
  const filas = partidas.length ? partidas : Object.entries(eco.desglose).map(([k, v]) => ({
    concepto: k, categoria: k, presupuestado: null, real: v, _virtual: true,
  }));
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', {}, ['Presupuestado frente a real ', el('span', { class: 'sub', txt: partidas.length ? '' : '(estimado a partir de consumos, subcontratas, maquinaria y personal)' })]),
    el('div', { class: 'tabla-caja' }, [
      el('table', {}, [
        el('thead', {}, [el('tr', {}, ['Concepto', 'Categoría', 'Presupuestado', 'Real', 'Desviación', ''].map((h) => el('th', { txt: h })))]),
        el('tbody', {}, filas.map((p) => {
          const pres = Number(p.presupuestado || 0);
          const real = Number(p.real || 0);
          const desv = real - pres;
          return el('tr', {
            onClick: () => !p._virtual && abrirDetalle('partidas', p.id, host),
          }, [
            el('td', { txt: p.concepto }),
            el('td', { txt: p.categoria || '' }),
            el('td', { class: 'num', txt: pres ? eur(pres) : '—' }),
            el('td', { class: 'num', txt: eur(real) }),
            el('td', { class: 'num', estilo: { color: desv > 0 ? 'var(--mal)' : 'var(--ok)', fontWeight: '600' }, txt: pres ? eur(desv) : '—' }),
            el('td', {}, [pres ? etiqueta(desv > 0 ? 'Desviada' : 'OK', desv > 0 ? 'mal' : 'ok') : el('span')]),
          ]);
        })),
      ]),
    ]),
  ]));

  // Stock valorado
  const conAlerta = stock.filter((s) => s.alerta !== 'OK');
  host.appendChild(el('div', { class: 'tarjeta' }, [
    el('h2', {}, ['Stock de material ', el('span', { class: 'sub', txt: `${conAlerta.length} con alerta` })]),
    stock.length ? el('div', { class: 'tabla-caja' }, [
      el('table', {}, [
        el('thead', {}, [el('tr', {}, ['Material', 'Recibido', 'Gastado', 'Restante', 'Valor restante', 'Alerta'].map((h) => el('th', { txt: h })))]),
        el('tbody', {}, stock.map((s) => el('tr', {
          onClick: () => abrirDetalle('materiales', s.id, host),
        }, [
          el('td', { txt: s.material }),
          el('td', { class: 'num', txt: num(s.recibido, 2) }),
          el('td', { class: 'num', txt: num(s.gastado, 2) }),
          el('td', { class: 'num', estilo: { fontWeight: '600', color: s.restante < 0 ? 'var(--mal)' : '' }, txt: num(s.restante, 2) }),
          el('td', { class: 'num', txt: eur(s.valor_restante) }),
          el('td', {}, [etiqueta(s.alerta)]),
        ]))),
      ]),
    ]) : el('p', { class: 'kpi-pie', txt: 'Sin materiales dados de alta.' }),
  ]));
}

// ═══════════════════════════════════════════════════════ ficha de obra
export async function vistaObra(host) {
  if (!estado.obraId) return vistaMultiObra(host);
  limpiar(host).appendChild(cargando());
  const obra = await api.obtener('obras', estado.obraId);
  limpiar(host);
  const ent = estado.meta.entidades.obras;

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [el('h1', { txt: '🏗️ Ficha de la obra' }), el('div', { class: 'sub', txt: obra.nombre })]),
    obra.coordenadas ? el('button', {
      class: 'btn btn-peq', txt: '📍 Mapa',
      onClick: () => window.open(`https://www.google.com/maps?q=${encodeURIComponent(obra.coordenadas)}`, '_blank'),
    }) : null,
    obra.carpeta ? el('button', {
      class: 'btn btn-peq', txt: '📁 Crear carpetas',
      onClick: async () => {
        try {
          const r = await api.crearCarpetas(estado.obraId);
          exito(`Estructura creada en ${r.carpeta}`);
        } catch (e) { error(e.message); }
      },
    }) : null,
    el('button', {
      class: 'btn btn-pri btn-peq', txt: '✏️ Editar',
      onClick: () => editar('obras', obra, { alGuardar: () => { window.obrasec.recargarObras(); vistaObra(host); } }),
    }),
  ]));

  for (const grupo of ent.groups) {
    const campos = ent.fields.filter((f) => f.group === grupo
      && obra[f.name] !== null && obra[f.name] !== undefined && obra[f.name] !== '');
    if (!campos.length) continue;
    host.appendChild(el('div', { class: 'tarjeta' }, [
      el('h2', { txt: grupo }),
      el('dl', { class: 'lista-def' }, campos.flatMap((c) => [
        el('dt', { txt: c.label }),
        el('dd', {}, [valorCelda(c, obra)]),
      ])),
    ]));
  }
}

// ═══════════════════════════════════════════════════════════ galería
export async function vistaFotos(host) {
  if (!estado.obraId) return limpiar(host).appendChild(vacio({ icono: '📸', titulo: 'Selecciona una obra' }));
  limpiar(host).appendChild(cargando());
  const lista = await api.adjuntosObra(estado.obraId);
  limpiar(host);

  host.appendChild(el('div', { class: 'vista-cab' }, [
    el('div', {}, [el('h1', { txt: '📸 Fotos y documentos' }), el('div', { class: 'sub', txt: `${lista.length} archivos` })]),
    el('button', {
      class: 'btn btn-pri btn-peq', txt: '📷 Añadir',
      onClick: () => window.obrasec.subirArchivo({
        entidad: 'obras', registroId: estado.obraId, camara: true, alSubir: () => vistaFotos(host),
      }),
    }),
  ]));

  if (!lista.length) {
    return host.appendChild(vacio({
      icono: '📸', titulo: 'Sin fotos todavía',
      texto: 'El reportaje fotográfico es tu mejor defensa ante una reclamación. Haz fotos del antes, del durante y del después de cada zona.',
      accion: {
        texto: '📷 Hacer la primera foto',
        alPulsar: () => window.obrasec.subirArchivo({
          entidad: 'obras', registroId: estado.obraId, camara: true, alSubir: () => vistaFotos(host),
        }),
      },
    }));
  }

  host.appendChild(el('div', { class: 'galeria' }, lista.map((a) => {
    const url = `/api/adjuntos/${a.id}/archivo`;
    const esImagen = (a.mime || '').startsWith('image/');
    const nodo = esImagen ? el('img', { src: url, loading: 'lazy', alt: a.nombre })
      : el('div', { class: 'doc', txt: '📄', title: a.nombre });
    nodo.addEventListener('click', () => modal({
      titulo: a.nombre,
      cuerpo: el('div', { estilo: { textAlign: 'center' } }, [
        esImagen ? el('img', { src: url, estilo: { maxWidth: '100%', borderRadius: '10px' } }) : null,
        el('p', { class: 'kpi-pie', txt: `${a.entidad} · ${fecha(a.creado)}` }),
      ]),
      acciones: [
        {
          texto: '🗑', clase: 'btn-mal',
          accion: async () => {
            if (!await confirmar('¿Eliminar este archivo?')) return false;
            await api.borrarAdjunto(a.id);
            await vistaFotos(host);
          },
        },
        { texto: '⬇ Descargar', accion: () => { descargar(url); return false; }, cargando: false },
        { texto: 'Cerrar' },
      ],
    }));
    return nodo;
  })));
}

// ═════════════════════════════════════════════════════════ informes
export async function dialogoInforme() {
  if (!estado.obraId) return error('Selecciona una obra primero');
  const plantillas = await api.plantillas();

  const cuerpo = el('div', {}, [
    el('div', { class: 'aviso-caja info' },
      'El informe se genera con los datos actuales de la obra. Si subes tus propias plantillas de Word, se rellenan conservando tu membrete y formato.'),
    el('div', { class: 'campo' }, [
      el('label', { txt: 'Plantilla' }),
      el('select', { id: 'sel-plantilla' }, [
        el('option', { value: '', txt: 'Informe de seguimiento estándar' }),
        ...plantillas.map((p) => el('option', { value: p.id, txt: p.nombre })),
      ]),
      el('div', { class: 'ayuda', txt: 'Gestiona tus plantillas en Ajustes › Plantillas de informe.' }),
    ]),
  ]);

  modal({
    titulo: '📄 Generar informe',
    cuerpo,
    acciones: [
      { texto: 'Cancelar' },
      {
        texto: 'Generar', clase: 'btn-pri',
        accion: () => {
          const id = $('#sel-plantilla', cuerpo).value;
          descargar(`/api/informes/${estado.obraId}${id ? `?plantilla=${id}` : ''}`);
          info('Generando el documento…');
        },
      },
    ],
  });
}

// Navegación (la implementa app.js y la expone aquí para evitar dependencias circulares).
export function irA(vista) { window.obrasec.irA(vista); }
