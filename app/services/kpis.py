"""
Cuadro de mando y sistema de alertas.

Las alertas son el valor real de la aplicación: replican lo que un jefe de obra
con experiencia comprueba cada mañana antes de pisar la obra. Cada regla tiene
severidad, mensaje accionable y enlace directo al módulo donde se resuelve.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from .. import db


def _fecha(valor) -> date | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor)[:10]).date()
    except ValueError:
        return None


def _dias_hasta(valor) -> int | None:
    f = _fecha(valor)
    return (f - date.today()).days if f else None


ESTADOS_CERRADOS = ("Completada", "Cancelada")


# ═══════════════════════════════════════════════════════════════════ KPIs
def resumen(obra_id: int) -> dict:
    obra = db.obtener("obras", obra_id) or {}

    tareas = db.listar("tareas", obra_id)
    total_t = len(tareas)
    completadas = sum(1 for t in tareas if t.get("estado") == "Completada")
    en_curso = sum(1 for t in tareas if t.get("estado") == "En curso")
    bloqueadas = sum(1 for t in tareas if t.get("estado") == "Bloqueada")
    # Avance ponderado por el % de cada tarea, no por número de tareas cerradas.
    avance = 0.0
    activas = [t for t in tareas if t.get("estado") != "Cancelada"]
    if activas:
        avance = sum(float(t.get("avance") or 0) for t in activas) / len(activas)

    retrasadas = [
        t for t in tareas
        if t.get("estado") not in ESTADOS_CERRADOS
        and (d := _dias_hasta(t.get("fecha_fin"))) is not None and d < 0
    ]

    disp = db.listar("dispositivos", obra_id)
    instalados = sum(
        1 for d in disp
        if d.get("estado") in ("Instalado", "Conexionado", "Configurado", "Probado", "Entregado")
    )
    probados = sum(1 for d in disp if d.get("estado") in ("Probado", "Entregado"))
    unidades = sum(int(d.get("cantidad") or 1) for d in disp)

    # Económico
    presupuestado = db.suma("partidas", "presupuestado", obra_id)
    coste_real = db.suma("partidas", "real", obra_id)
    comprometido = db.suma("partidas", "comprometido", obra_id)
    coste_material = sum(
        float(c.get("cantidad") or 0) * _precio_material(c.get("material_id"))
        for c in db.listar("consumos", obra_id)
    )
    coste_subs = db.suma("subcontratas", "importe_certificado", obra_id)
    coste_maq = _coste_maquinaria(obra_id)
    coste_mo = _coste_personal(obra_id)
    coste_calculado = coste_material + coste_subs + coste_maq + coste_mo
    coste_total = max(coste_real, coste_calculado)

    ampliaciones = db.suma("ofertas", "importe", obra_id, estado="Aprobada")
    contrato = float(obra.get("importe_contrato") or 0)
    ingresos = contrato + ampliaciones
    margen = ingresos - coste_total
    margen_pct = (margen / ingresos * 100) if ingresos else 0.0

    certificado = db.suma("certificaciones", "importe", obra_id)
    cobrado = db.suma("certificaciones", "importe", obra_id, estado="Cobrada")

    incidencias_abiertas = sum(
        1 for i in db.listar("incidencias", obra_id)
        if i.get("estado") in ("Abierta", "En gestión", "Escalada")
    )
    docs_pendientes = sum(
        1 for d in db.listar("documentos", obra_id)
        if d.get("estado") in ("Pendiente", "Solicitada", "En revisión")
    )

    # Plazo
    dias_restantes = _dias_hasta(obra.get("fecha_fin_prevista"))
    dias_totales = None
    consumido_pct = None
    fi, ff = _fecha(obra.get("fecha_inicio")), _fecha(obra.get("fecha_fin_prevista"))
    if fi and ff and ff > fi:
        dias_totales = (ff - fi).days
        transcurridos = (date.today() - fi).days
        consumido_pct = max(0.0, min(100.0, transcurridos / dias_totales * 100))

    return {
        "obra": obra,
        "tareas": {
            "total": total_t, "completadas": completadas, "en_curso": en_curso,
            "bloqueadas": bloqueadas, "retrasadas": len(retrasadas),
            "avance": round(avance, 1),
            "por_estado": _agrupar(tareas, "estado"),
            "por_categoria": _agrupar(tareas, "categoria"),
        },
        "dispositivos": {
            "total": len(disp), "unidades": unidades, "instalados": instalados,
            "probados": probados,
            "pct_instalado": round(instalados / len(disp) * 100, 1) if disp else 0,
            "por_estado": _agrupar(disp, "estado"),
            "por_categoria": _agrupar(disp, "categoria"),
        },
        "economico": {
            "contrato": contrato, "ampliaciones": ampliaciones, "ingresos": ingresos,
            "presupuestado": presupuestado, "comprometido": comprometido,
            "coste_total": round(coste_total, 2),
            "desglose": {
                "Material": round(coste_material, 2),
                "Subcontratas": round(coste_subs, 2),
                "Maquinaria": round(coste_maq, 2),
                "Mano de obra": round(coste_mo, 2),
            },
            "margen": round(margen, 2), "margen_pct": round(margen_pct, 1),
            "certificado": certificado, "cobrado": cobrado,
            "pendiente_cobro": round(certificado - cobrado, 2),
        },
        "plazo": {
            "dias_restantes": dias_restantes, "dias_totales": dias_totales,
            "consumido_pct": round(consumido_pct, 1) if consumido_pct is not None else None,
            "desviacion": (round(consumido_pct - avance, 1)
                           if consumido_pct is not None else None),
        },
        "otros": {
            "incidencias_abiertas": incidencias_abiertas,
            "docs_pendientes": docs_pendientes,
            "subcontratas": db.contar("subcontratas", obra_id),
            "personal": db.contar("personal", obra_id),
            "personal_con_acceso": db.contar("personal", obra_id, estado="ACCESS"),
            "maquinaria": db.contar("maquinaria", obra_id),
            "fotos": len(db.adjuntos_obra(obra_id)),
        },
        "alertas": alertas(obra_id),
    }


def _agrupar(filas: list[dict], campo: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in filas:
        k = f.get(campo) or "(sin definir)"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _precio_material(material_id) -> float:
    if not material_id:
        return 0.0
    m = db.obtener("materiales", int(material_id))
    return float((m or {}).get("precio") or 0)


def _coste_maquinaria(obra_id: int) -> float:
    total = 0.0
    for m in db.listar("maquinaria", obra_id):
        coste_dia = float(m.get("coste_dia") or 0)
        total += float(m.get("coste_transporte") or 0)
        ent, sal = _fecha(m.get("fecha_entrada")), _fecha(m.get("fecha_salida"))
        if ent and coste_dia:
            fin = sal or date.today()
            total += max(0, (fin - ent).days) * coste_dia
    return total


def _coste_personal(obra_id: int) -> float:
    return sum(
        float(p.get("horas") or 0) * float(p.get("precio_hora") or 0)
        for p in db.listar("personal", obra_id)
    )


# ═══════════════════════════════════════════════════════════ stock material
def stock(obra_id: int) -> list[dict]:
    """Recibido menos consumido, con alerta de reposición y exceso."""
    consumido: dict[int, float] = {}
    for c in db.listar("consumos", obra_id):
        mid = c.get("material_id")
        if mid:
            consumido[int(mid)] = consumido.get(int(mid), 0) + float(c.get("cantidad") or 0)

    filas = []
    for m in db.listar("materiales", obra_id):
        recibido = float(m.get("recibido") or 0)
        gastado = consumido.get(m["id"], 0.0)
        restante = recibido - gastado
        minimo = float(m.get("stock_min") or 0)
        precio = float(m.get("precio") or 0)
        if restante < 0:
            estado = "EXCEDIDO"
        elif minimo and restante <= minimo:
            estado = "REPONER"
        elif recibido and restante == 0:
            estado = "AGOTADO"
        else:
            estado = "OK"
        filas.append({
            **m, "gastado": round(gastado, 2), "restante": round(restante, 2),
            "pct_consumido": round(gastado / recibido * 100, 1) if recibido else 0,
            "valor_gastado": round(gastado * precio, 2),
            "valor_restante": round(restante * precio, 2),
            "alerta": estado,
        })
    return filas


# ═══════════════════════════════════════════════════════════════ alertas
def alertas(obra_id: int) -> list[dict]:
    """Reglas de vigilancia diaria. Severidad: critica | alta | media | info."""
    out: list[dict] = []

    def add(sev: str, titulo: str, detalle: str, modulo: str, n: int = 1):
        out.append({"severidad": sev, "titulo": titulo, "detalle": detalle,
                    "modulo": modulo, "n": n})

    hoy = date.today()

    # ── Tareas fuera de plazo o bloqueadas ────────────────────────────────
    retrasadas, proximas, bloqueadas = [], [], []
    for t in db.listar("tareas", obra_id):
        if t.get("estado") == "Bloqueada":
            bloqueadas.append(t)
        if t.get("estado") in ESTADOS_CERRADOS:
            continue
        d = _dias_hasta(t.get("fecha_fin"))
        if d is None:
            continue
        if d < 0:
            retrasadas.append((t, d))
        elif d <= 3:
            proximas.append((t, d))
    if retrasadas:
        peor = min(retrasadas, key=lambda x: x[1])
        add("critica", f"{len(retrasadas)} tarea(s) fuera de plazo",
            f"La más retrasada: «{peor[0].get('tarea')}» con {abs(peor[1])} días de retraso.",
            "tareas", len(retrasadas))
    if bloqueadas:
        add("alta", f"{len(bloqueadas)} tarea(s) bloqueadas",
            "Una tarea bloqueada no avanza sola: identifica el impedimento y escálalo hoy.",
            "tareas", len(bloqueadas))
    if proximas:
        add("media", f"{len(proximas)} tarea(s) vencen en 3 días",
            "Confirma que la subcontrata tiene material y acceso para cerrarlas.",
            "tareas", len(proximas))

    # ── Desviación plazo vs avance ────────────────────────────────────────
    obra = db.obtener("obras", obra_id) or {}
    fi, ff = _fecha(obra.get("fecha_inicio")), _fecha(obra.get("fecha_fin_prevista"))
    tareas = db.listar("tareas", obra_id)
    activas = [t for t in tareas if t.get("estado") != "Cancelada"]
    if fi and ff and ff > fi and activas:
        transcurrido = (hoy - fi).days / (ff - fi).days * 100
        avance = sum(float(t.get("avance") or 0) for t in activas) / len(activas)
        if transcurrido - avance > 15:
            add("critica", "La obra va por detrás del calendario",
                f"Plazo consumido {transcurrido:.0f}% frente a un avance real del {avance:.0f}%. "
                f"Desviación de {transcurrido - avance:.0f} puntos.", "gantt")
        elif transcurrido - avance > 7:
            add("media", "Avance ligeramente por detrás del plazo",
                f"Consumido {transcurrido:.0f}% del plazo, avance {avance:.0f}%.", "gantt")
    if ff:
        d = (ff - hoy).days
        if d < 0 and obra.get("estado") not in ("Finalizada", "Cancelada", "Garantía"):
            add("critica", "Fecha de fin superada",
                f"La fecha fin prevista era hace {abs(d)} días y la obra sigue abierta. "
                f"Revisa penalizaciones y solicita ampliación de plazo por escrito.", "obra")
        elif 0 <= d <= 7:
            add("alta", f"Quedan {d} días para la fecha de entrega",
                "Cierra pruebas, documentación as-built y acta de recepción.", "obra")

    # ── Material ──────────────────────────────────────────────────────────
    reponer = [s for s in stock(obra_id) if s["alerta"] == "REPONER"]
    excedido = [s for s in stock(obra_id) if s["alerta"] == "EXCEDIDO"]
    if excedido:
        add("alta", f"{len(excedido)} material(es) con consumo superior al recibido",
            "O falta registrar una recepción, o hay un error de imputación. "
            f"Ej.: {excedido[0].get('material')}.", "materiales", len(excedido))
    if reponer:
        add("media", f"{len(reponer)} material(es) bajo mínimo",
            f"Lanza pedido antes de que pare el tajo. Ej.: {reponer[0].get('material')}.",
            "materiales", len(reponer))

    # ── Incidencias ───────────────────────────────────────────────────────
    graves = 0
    vencidas = 0
    for i in db.listar("incidencias", obra_id):
        if i.get("estado") in ("Resuelta", "Cerrada"):
            continue
        if i.get("gravedad") in ("Grave", "Crítica"):
            graves += 1
        d = _dias_hasta(i.get("fecha_limite"))
        if d is not None and d < 0:
            vencidas += 1
    if graves:
        add("critica", f"{graves} incidencia(s) grave(s) sin cerrar",
            "Documenta la acción correctiva y comunica al cliente por escrito.",
            "incidencias", graves)
    if vencidas:
        add("alta", f"{vencidas} incidencia(s) con fecha límite vencida",
            "Reasigna responsable o escala al cliente.", "incidencias", vencidas)

    # ── Subcontratas: PRL, seguro, REA ────────────────────────────────────
    sin_seguro, seguro_vence, sin_prl, sin_contrato = [], [], [], []
    for s in db.listar("subcontratas", obra_id):
        if s.get("estado") in ("Finalizada", "Vetada"):
            continue
        if s.get("seguro_rc") == "No":
            sin_seguro.append(s)
        d = _dias_hasta(s.get("seguro_rc_vence"))
        if d is not None and d < 30:
            seguro_vence.append((s, d))
        if s.get("prl_ok") == "No":
            sin_prl.append(s)
        if s.get("estado") == "Activa" and not s.get("contrato_firmado"):
            sin_contrato.append(s)
    if sin_seguro:
        add("critica", f"{len(sin_seguro)} subcontrata(s) sin seguro RC acreditado",
            "No pueden trabajar en obra. Si hay un accidente, la responsabilidad sube por "
            f"la cadena. Ej.: {sin_seguro[0].get('nombre')}.", "subcontratas", len(sin_seguro))
    if sin_prl:
        add("critica", f"{len(sin_prl)} subcontrata(s) sin documentación PRL/CAE",
            "Bloquea su acceso hasta que suban la documentación a la plataforma CAE.",
            "subcontratas", len(sin_prl))
    if seguro_vence:
        s, d = seguro_vence[0]
        add("alta", f"{len(seguro_vence)} seguro(s) RC vencen en menos de 30 días",
            f"«{s.get('nombre')}»: {'vencido hace ' + str(abs(d)) if d < 0 else 'quedan ' + str(d)} días.",
            "subcontratas", len(seguro_vence))
    if sin_contrato:
        add("media", f"{len(sin_contrato)} subcontrata(s) activas sin contrato firmado",
            "Trabajar sin contrato firmado te deja sin respaldo ante desviaciones de precio.",
            "subcontratas", len(sin_contrato))

    # ── Personal: accesos y caducidades ───────────────────────────────────
    sin_acceso, medico, validando = [], [], []
    for p in db.listar("personal", obra_id):
        if p.get("estado") == "BAJA":
            continue
        if p.get("estado") == "NO ACCESS":
            sin_acceso.append(p)
        if p.get("estado") == "VALIDANDO":
            validando.append(p)
        d = _dias_hasta(p.get("medico_vence"))
        if d is not None and d < 30:
            medico.append((p, d))
    if sin_acceso:
        add("alta", f"{len(sin_acceso)} persona(s) sin acceso autorizado",
            "No entran a la nave. Tramita la acreditación antes del próximo tajo.",
            "personal", len(sin_acceso))
    if validando:
        add("media", f"{len(validando)} acreditación(es) en validación",
            "Persigue al departamento de CAE: suelen tardar más de lo que dicen.",
            "personal", len(validando))
    if medico:
        add("alta", f"{len(medico)} reconocimiento(s) médico(s) por caducar",
            f"Ej.: {medico[0][0].get('nombre')}. Sin él, no puede acceder.",
            "personal", len(medico))

    # ── Maquinaria: ITV y seguros ─────────────────────────────────────────
    itv, seguro_maq = [], []
    for m in db.listar("maquinaria", obra_id):
        if m.get("estado") in ("Devuelta",):
            continue
        d = _dias_hasta(m.get("proxima_itv"))
        if d is not None and d < 30:
            itv.append((m, d))
        d2 = _dias_hasta(m.get("seguro_vence"))
        if d2 is not None and d2 < 15:
            seguro_maq.append(m)
    if itv:
        m, d = itv[0]
        add("alta", f"{len(itv)} equipo(s) con ITV/revisión próxima o vencida",
            f"«{m.get('equipo')}»: {'vencida hace ' + str(abs(d)) if d < 0 else str(d)} días. "
            "Una PEMP sin revisión en vigor es una parada de obra si hay inspección.",
            "maquinaria", len(itv))
    if seguro_maq:
        add("media", f"{len(seguro_maq)} equipo(s) con seguro por vencer", "",
            "maquinaria", len(seguro_maq))

    # ── Documentación ─────────────────────────────────────────────────────
    docs_venc, docs_oblig = [], []
    for doc in db.listar("documentos", obra_id):
        if doc.get("estado") in ("Completada", "No procede"):
            continue
        d = _dias_hasta(doc.get("fecha_limite"))
        if d is not None and d < 0:
            docs_venc.append(doc)
        if doc.get("obligatorio"):
            docs_oblig.append(doc)
    if docs_venc:
        add("alta", f"{len(docs_venc)} documento(s) con fecha límite vencida",
            f"Ej.: {docs_venc[0].get('documento')}.", "documentos", len(docs_venc))
    if docs_oblig:
        add("media", f"{len(docs_oblig)} documento(s) obligatorios pendientes",
            "Sin ellos no se firma el acta de recepción ni se cobra la última certificación.",
            "documentos", len(docs_oblig))

    # ── Ofertas sin respuesta ─────────────────────────────────────────────
    enviadas = []
    for o in db.listar("ofertas", obra_id):
        if o.get("estado") != "Enviada":
            continue
        d = _dias_hasta(o.get("fecha_envio"))
        if d is not None and d < -10:
            enviadas.append((o, abs(d)))
    if enviadas:
        total = sum(float(o.get("importe") or 0) for o, _ in enviadas)
        add("alta", f"{len(enviadas)} ampliación(es) enviadas sin respuesta",
            f"{total:,.0f} € parados desde hace más de 10 días. Si el trabajo ya se está "
            "ejecutando sin aprobación por escrito, estás financiando al cliente.".replace(",", "."),
            "ofertas", len(enviadas))

    # ── Económico ─────────────────────────────────────────────────────────
    r_eco = _economico_simple(obra_id, obra)
    if r_eco["ingresos"] and r_eco["margen_pct"] < 0:
        add("critica", "La obra está en pérdidas",
            f"Coste {r_eco['coste']:,.0f} € frente a ingresos {r_eco['ingresos']:,.0f} €. "
            "Revisa ampliaciones no ofertadas y desviaciones de subcontrata.".replace(",", "."),
            "economico")
    elif r_eco["ingresos"] and r_eco["margen_pct"] < 10:
        add("alta", f"Margen bajo: {r_eco['margen_pct']:.1f}%",
            "Por debajo del 10% cualquier imprevisto se come el beneficio.", "economico")
    if not obra.get("importe_contrato"):
        add("info", "Falta el importe del contrato",
            "Sin él no se puede calcular margen ni desviación económica.", "obra")

    pendiente = db.suma("certificaciones", "importe", obra_id) - \
        db.suma("certificaciones", "importe", obra_id, estado="Cobrada")
    vencido_cobro = 0
    for c in db.listar("certificaciones", obra_id):
        if c.get("estado") == "Cobrada":
            continue
        d = _dias_hasta(c.get("fecha_cobro_prevista"))
        if d is not None and d < 0:
            vencido_cobro += 1
    if vencido_cobro:
        add("alta", f"{vencido_cobro} certificación(es) con cobro vencido",
            f"Pendiente de cobro total: {pendiente:,.0f} €.".replace(",", "."), "certificaciones")

    # ── Inventario de instalación ─────────────────────────────────────────
    disp = db.listar("dispositivos", obra_id)
    ips: dict[str, list[str]] = {}
    sin_serie, sin_probar, averiados = 0, 0, 0
    for d in disp:
        ip = (d.get("ip") or "").strip()
        if ip:
            ips.setdefault(ip, []).append(d.get("etiqueta") or f"#{d['id']}")
        if d.get("estado") in ("Instalado", "Conexionado", "Configurado", "Entregado") \
                and not d.get("num_serie"):
            sin_serie += 1
        if d.get("estado") in ("Instalado", "Conexionado", "Configurado") \
                and d.get("prueba_visual") in (None, "", "Pendiente"):
            sin_probar += 1
        if d.get("estado") in ("Averiado", "Pendiente sustitución"):
            averiados += 1
    duplicadas = {ip: eq for ip, eq in ips.items() if len(eq) > 1}
    if duplicadas:
        ip, eq = next(iter(duplicadas.items()))
        add("critica", f"{len(duplicadas)} dirección(es) IP duplicada(s)",
            f"{ip} está asignada a: {', '.join(eq)}. Provoca caídas intermitentes "
            "que luego cuesta horas diagnosticar.", "dispositivos", len(duplicadas))
    if averiados:
        add("alta", f"{averiados} dispositivo(s) averiados o pendientes de sustitución",
            "Tramita RMA y deja constancia: afecta a la garantía y al acta de recepción.",
            "dispositivos", averiados)
    if sin_serie:
        add("media", f"{sin_serie} dispositivo(s) instalados sin número de serie",
            "Sin S/N no hay garantía ni inventario válido para el cliente. "
            "Haz foto a la etiqueta desde el móvil y deja que la IA lo rellene.",
            "dispositivos", sin_serie)
    if sin_probar:
        add("media", f"{sin_probar} dispositivo(s) instalados sin pruebas registradas",
            "Las pruebas se firman al final, pero se registran el día que se hacen.",
            "dispositivos", sin_probar)

    orden = {"critica": 0, "alta": 1, "media": 2, "info": 3}
    return sorted(out, key=lambda a: (orden.get(a["severidad"], 9), -a["n"]))


def _economico_simple(obra_id: int, obra: dict) -> dict:
    coste = (
        sum(float(c.get("cantidad") or 0) * _precio_material(c.get("material_id"))
            for c in db.listar("consumos", obra_id))
        + db.suma("subcontratas", "importe_certificado", obra_id)
        + _coste_maquinaria(obra_id) + _coste_personal(obra_id)
    )
    coste = max(coste, db.suma("partidas", "real", obra_id))
    ingresos = float(obra.get("importe_contrato") or 0) + \
        db.suma("ofertas", "importe", obra_id, estado="Aprobada")
    return {
        "coste": coste, "ingresos": ingresos,
        "margen_pct": ((ingresos - coste) / ingresos * 100) if ingresos else 0,
    }


# ═══════════════════════════════════════════════════════════════════ Gantt
def gantt(obra_id: int) -> dict:
    """Datos para el diagrama de Gantt, con ruta y estado por tarea."""
    tareas = db.listar("tareas", obra_id)
    filas, minimo, maximo = [], None, None
    for t in tareas:
        ini, fin = _fecha(t.get("fecha_inicio")), _fecha(t.get("fecha_fin"))
        if not ini and not fin:
            continue
        ini = ini or fin
        fin = fin or ini
        if fin < ini:
            ini, fin = fin, ini
        minimo = ini if minimo is None or ini < minimo else minimo
        maximo = fin if maximo is None or fin > maximo else maximo
        d = (fin - date.today()).days
        estado = t.get("estado")
        if estado == "Completada":
            color = "ok"
        elif estado == "Bloqueada":
            color = "bloq"
        elif estado not in ESTADOS_CERRADOS and d < 0:
            color = "retraso"
        elif estado == "En curso":
            color = "curso"
        else:
            color = "plan"
        filas.append({
            "id": t["id"], "tarea": t.get("tarea"), "categoria": t.get("categoria"),
            "estado": estado, "avance": float(t.get("avance") or 0),
            "inicio": ini.isoformat(), "fin": fin.isoformat(),
            "dias": (fin - ini).days + 1, "color": color,
            "responsable": t.get("responsable"), "hito": bool(t.get("hito")),
            "depende_de": t.get("depende_de"),
        })
    filas.sort(key=lambda f: (f["inicio"], f["fin"]))
    return {
        "tareas": filas,
        "desde": (minimo or date.today()).isoformat(),
        "hasta": (maximo or date.today() + timedelta(days=30)).isoformat(),
        "hoy": date.today().isoformat(),
    }


# ═══════════════════════════════════════════════════ contexto para la IA
def contexto_ia(obra_id: int) -> dict:
    """Fotografía compacta de la obra para dársela al asistente."""
    r = resumen(obra_id)
    obra = r["obra"]
    return {
        "obra": {k: obra.get(k) for k in (
            "nombre", "codigo", "cliente", "cliente_final", "poblacion", "estado",
            "fecha_inicio", "fecha_fin_prevista", "importe_contrato", "jefe_obra",
            "alcance", "tipo_instalacion",
        ) if obra.get(k)},
        "indicadores": {
            "avance_pct": r["tareas"]["avance"],
            "tareas": r["tareas"],
            "dispositivos": r["dispositivos"],
            "economico": r["economico"],
            "plazo": r["plazo"],
        },
        "alertas_activas": [
            {"severidad": a["severidad"], "titulo": a["titulo"]} for a in r["alertas"]
        ],
        "tareas_abiertas": [
            {k: t.get(k) for k in ("tarea", "estado", "avance", "fecha_fin", "responsable", "categoria")}
            for t in db.listar("tareas", obra_id)
            if t.get("estado") not in ESTADOS_CERRADOS
        ][:60],
        "incidencias_abiertas": [
            {k: i.get(k) for k in ("titulo", "gravedad", "estado", "fecha_limite", "responsable")}
            for i in db.listar("incidencias", obra_id)
            if i.get("estado") not in ("Resuelta", "Cerrada")
        ][:40],
        "subcontratas": [
            {k: s.get(k) for k in ("nombre", "especialidad", "estado", "importe_contratado",
                                   "importe_certificado", "seguro_rc", "prl_ok")}
            for s in db.listar("subcontratas", obra_id)
        ][:30],
        "material_critico": [
            {k: s.get(k) for k in ("material", "restante", "stock_min", "alerta", "proveedor")}
            for s in stock(obra_id) if s["alerta"] != "OK"
        ][:40],
        "dispositivos_resumen": _agrupar(db.listar("dispositivos", obra_id), "estado"),
    }
