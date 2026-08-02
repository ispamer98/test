"""
Prueba de humo completa de ObraSec.

Recorre el ciclo real de una obra —alta, tareas, inventario, consumos,
alertas, exportación e informe— contra la aplicación entera, sin levantar
un servidor de verdad. Es la red de seguridad antes de publicar una versión.

    python tests/test_humo.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = Path(tempfile.mkdtemp(prefix="obrasec_test_"))
os.environ["OBRASEC_DATA"] = str(DATOS)
sys.path.insert(0, str(RAIZ))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

fallos = []


def check(nombre, cond, extra=""):
    print(("  OK  " if cond else "  FALLO ") + nombre + (f"  {extra}" if extra and not cond else ""))
    if not cond:
        fallos.append(nombre)


with TestClient(app) as c:
    # ── metadatos ────────────────────────────────────────────────────
    r = c.get("/api/estado")
    check("GET /api/estado", r.status_code == 200, r.text[:200])
    r = c.get("/api/meta")
    check("GET /api/meta", r.status_code == 200, r.text[:200])
    meta = r.json()
    check("meta trae 17 entidades", len(meta["entidades"]) == 17, str(len(meta["entidades"])))
    check("meta trae catálogos", len(meta["catalogos"]) > 25, str(len(meta["catalogos"])))

    # ── obra ─────────────────────────────────────────────────────────
    r = c.post("/api/e/obras", json={
        "nombre": "CD Illescas - Nave 3", "codigo": "OT2X-44821",
        "cliente": "Telefónica Soluciones", "cliente_final": "DHL Supply Chain",
        "estado": "En curso", "poblacion": "Illescas", "provincia": "Toledo",
        "jefe_obra": "Rubén", "fecha_inicio": "2026-06-01",
        "fecha_fin_prevista": "2026-07-15", "importe_contrato": 84500,
        "tipo_instalacion": "Nave logística", "num_camaras": 42,
        "rango_ip": "10.40.12.0/24",
    })
    check("POST /api/e/obras", r.status_code == 200, r.text[:300])
    obra = r.json()
    oid = obra["id"]

    # ── tareas ───────────────────────────────────────────────────────
    tareas = [
        {"tarea": "Replanteo con cliente", "categoria": "Replanteo", "estado": "Completada",
         "avance": 100, "fecha_inicio": "2026-06-01", "fecha_fin": "2026-06-02", "prioridad": "Alta"},
        {"tarea": "Canalización muelles", "categoria": "Canalización", "estado": "En curso",
         "avance": 60, "fecha_inicio": "2026-06-03", "fecha_fin": "2026-06-20", "prioridad": "Alta"},
        {"tarea": "Tirada UTP CAT6 planta", "categoria": "Cableado", "estado": "En curso",
         "avance": 35, "fecha_inicio": "2026-06-10", "fecha_fin": "2026-06-28"},
        {"tarea": "Montaje 42 cámaras", "categoria": "CCTV", "estado": "No iniciada",
         "avance": 0, "fecha_inicio": "2026-06-25", "fecha_fin": "2026-07-05"},
        {"tarea": "Alta en CRA y pruebas", "categoria": "Pruebas y Puesta en Marcha",
         "estado": "Bloqueada", "avance": 0, "fecha_inicio": "2026-07-06",
         "fecha_fin": "2026-07-10", "prioridad": "Crítica"},
        {"tarea": "Tarea vencida de prueba", "categoria": "CCTV", "estado": "En curso",
         "avance": 20, "fecha_inicio": "2026-01-01", "fecha_fin": "2026-02-01"},
    ]
    for t in tareas:
        r = c.post(f"/api/e/tareas?obra={oid}", json=t)
        if r.status_code != 200:
            check(f"POST tarea {t['tarea']}", False, r.text[:200])
    check("6 tareas creadas", len(c.get(f"/api/e/tareas?obra={oid}").json()) == 6)

    # ── dispositivos ─────────────────────────────────────────────────
    disp = [
        {"etiqueta": "CAM-MUELLE-01", "categoria": "CCTV", "tipo": "Cámara IP Bullet",
         "marca": "Hikvision", "modelo": "DS-2CD2686G2-IZS", "num_serie": "AA1234567890",
         "ip": "10.40.12.11", "mac": "44:47:CC:11:22:33", "zona": "Muelles de carga",
         "estado": "Instalado", "poe": "PoE+ (802.3at)", "prueba_visual": "OK"},
        {"etiqueta": "CAM-MUELLE-02", "categoria": "CCTV", "tipo": "Cámara IP Bullet",
         "marca": "Hikvision", "modelo": "DS-2CD2686G2-IZS", "num_serie": "AA1234567891",
         "ip": "10.40.12.12", "zona": "Muelles de carga", "estado": "Instalado"},
        # IP duplicada a propósito, para probar la alerta
        {"etiqueta": "CAM-PERIM-01", "categoria": "CCTV", "tipo": "Cámara IP PTZ",
         "marca": "Hikvision", "modelo": "DS-2DE4A425IWG", "ip": "10.40.12.12",
         "zona": "Perímetro Norte", "estado": "Instalado"},
        {"etiqueta": "NVR-SALA-01", "categoria": "CCTV", "tipo": "NVR", "marca": "Hikvision",
         "modelo": "DS-9664NI-I8", "num_serie": "BB998877", "ip": "10.40.12.5",
         "zona": "Sala técnica / CPD", "estado": "Configurado"},
        {"etiqueta": "LECT-ACC-01", "categoria": "Control de Accesos", "tipo": "Lector Proximidad",
         "marca": "Vanderbilt", "modelo": "AR-8", "zona": "Acceso peatonal", "estado": "Previsto"},
    ]
    for d in disp:
        r = c.post(f"/api/e/dispositivos?obra={oid}", json=d)
        if r.status_code != 200:
            check(f"POST dispositivo {d['etiqueta']}", False, r.text[:200])
    check("5 dispositivos creados", len(c.get(f"/api/e/dispositivos?obra={oid}").json()) == 5)

    # ── material y consumos ──────────────────────────────────────────
    r = c.post(f"/api/e/materiales?obra={oid}", json={
        "material": "UTP CAT6 exterior", "categoria": "Cableado", "unidad": "m",
        "recibido": 500, "precio": 0.62, "proveedor": "Redstone", "stock_min": 100})
    mat = r.json()
    check("POST material", r.status_code == 200, r.text[:200])
    c.post(f"/api/e/materiales?obra={oid}", json={
        "material": "Manguera 4+2", "categoria": "Cableado", "unidad": "m",
        "recibido": 300, "precio": 1.1, "proveedor": "Telefónica", "stock_min": 50})
    r = c.post(f"/api/e/consumos?obra={oid}", json={
        "fecha": "2026-06-12", "material_id": mat["id"], "cantidad": 420,
        "registrado_por": "Rubén"})
    check("POST consumo", r.status_code == 200, r.text[:200])

    # ── subcontrata sin seguro (dispara alerta crítica) ──────────────
    r = c.post(f"/api/e/subcontratas?obra={oid}", json={
        "nombre": "RS Sistemas", "cif": "B12345678", "especialidad": "CCTV",
        "estado": "Activa", "seguro_rc": "No", "prl_ok": "No",
        "importe_contratado": 21000, "importe_certificado": 8000})
    check("POST subcontrata", r.status_code == 200, r.text[:200])

    # ── personal, maquinaria, incidencia, documento ─────────────────
    c.post(f"/api/e/personal?obra={oid}", json={
        "nombre": "Juan Pérez", "dni": "12345678Z", "empresa": "RS Sistemas",
        "oficio": "Instalador", "estado": "NO ACCESS", "horas": 120, "precio_hora": 22})
    c.post(f"/api/e/maquinaria?obra={oid}", json={
        "equipo": "PEMP tijera 12m", "tipo": "PEMP Tijera", "propiedad": "Alquilada",
        "proveedor": "Loxam", "estado": "En obra", "coste_dia": 85,
        "fecha_entrada": "2026-06-05", "proxima_itv": "2026-06-20"})
    c.post(f"/api/e/incidencias?obra={oid}", json={
        "titulo": "Falta canalización en muelle 7", "fecha": "2026-06-11",
        "tipo": "Coordinación", "gravedad": "Grave", "estado": "Abierta",
        "responsable": "Constructora"})
    c.post(f"/api/e/documentos?obra={oid}", json={
        "documento": "Ficha datos CRA", "categoria": "Certificado", "estado": "Pendiente",
        "obligatorio": 1, "fecha_limite": "2026-06-01"})
    c.post(f"/api/e/ofertas?obra={oid}", json={
        "descripcion": "8 cámaras adicionales muelle 8", "importe": 6400,
        "estado": "Enviada", "fecha_envio": "2026-05-20", "motivo": "Ampliación de alcance"})

    # ── cuadro de mando ──────────────────────────────────────────────
    r = c.get(f"/api/obras/{oid}/resumen")
    check("GET resumen", r.status_code == 200, r.text[:300])
    res = r.json()
    print(f"      avance={res['tareas']['avance']}%  retrasadas={res['tareas']['retrasadas']}"
          f"  disp={res['dispositivos']['total']}  alertas={len(res['alertas'])}")
    check("hay alertas", len(res["alertas"]) > 5, str(len(res["alertas"])))
    titulos = [a["titulo"] for a in res["alertas"]]
    check("alerta de IP duplicada", any("IP duplicada" in t for t in titulos), str(titulos))
    check("alerta de seguro RC", any("seguro RC" in t for t in titulos), str(titulos))
    check("alerta de PRL", any("PRL" in t for t in titulos), str(titulos))
    check("alerta de tarea fuera de plazo", any("fuera de plazo" in t for t in titulos), str(titulos))
    check("margen calculado", res["economico"]["ingresos"] == 84500,
          str(res["economico"]))
    print(f"      coste={res['economico']['coste_total']} margen={res['economico']['margen_pct']}%")

    # ── stock ────────────────────────────────────────────────────────
    r = c.get(f"/api/obras/{oid}/stock")
    stock = r.json()
    utp = next(s for s in stock if s["material"] == "UTP CAT6 exterior")
    check("stock descuenta consumo", utp["restante"] == 80, str(utp["restante"]))
    check("alerta REPONER", utp["alerta"] == "REPONER", utp["alerta"])

    # ── gantt ────────────────────────────────────────────────────────
    r = c.get(f"/api/obras/{oid}/gantt")
    g = r.json()
    check("GET gantt", r.status_code == 200 and len(g["tareas"]) == 6, str(len(g.get("tareas", []))))
    colores = {t["color"] for t in g["tareas"]}
    check("gantt colorea estados", "ok" in colores and "retraso" in colores, str(colores))

    # ── validaciones ─────────────────────────────────────────────────
    r = c.get(f"/api/obras/{oid}/ip-libre?ip=10.40.12.12")
    check("detecta IP ocupada", r.json()["libre"] is False, r.text)
    r = c.get(f"/api/obras/{oid}/ip-libre?ip=10.40.12.99")
    check("detecta IP libre", r.json()["libre"] is True, r.text)
    r = c.get("/api/serie-existe?num_serie=AA1234567890")
    check("detecta serie repetida", r.json()["existe"] is True, r.text)

    # ── búsqueda ─────────────────────────────────────────────────────
    r = c.get(f"/api/buscar?q=MUELLE&obra={oid}")
    check("búsqueda global", r.status_code == 200 and len(r.json()) >= 2, r.text[:200])

    # ── panel multi-obra ─────────────────────────────────────────────
    r = c.get("/api/panel")
    check("GET panel", r.status_code == 200 and len(r.json()) == 1, r.text[:200])

    # ── duplicar ─────────────────────────────────────────────────────
    d1 = c.get(f"/api/e/dispositivos?obra={oid}").json()[0]
    r = c.post(f"/api/e/dispositivos/duplicar/{d1['id']}?veces=3")
    check("duplicar x3", r.status_code == 200 and r.json()["creados"] == 3, r.text[:200])
    nombres = [x["etiqueta"] for x in r.json()["registros"]]
    print(f"      duplicados: {nombres}")

    # ── exportación Excel ────────────────────────────────────────────
    r = c.get(f"/api/export/obra/{oid}")
    check("export libro Excel", r.status_code == 200 and len(r.content) > 8000,
          f"{r.status_code} {len(r.content)}")
    (DATOS / "prueba_export.xlsx").write_bytes(r.content)
    r = c.get(f"/api/export/dispositivos?obra={oid}")
    check("export inventario Excel", r.status_code == 200 and len(r.content) > 4000,
          f"{r.status_code} {len(r.content)}")

    # ── informe Word ─────────────────────────────────────────────────
    r = c.get(f"/api/informes/{oid}")
    check("informe Word estándar", r.status_code == 200 and len(r.content) > 10000,
          f"{r.status_code} {r.content[:200]}")
    (DATOS / "prueba_informe.docx").write_bytes(r.content)

    # ── copia de seguridad ───────────────────────────────────────────
    r = c.get("/api/backup")
    check("backup ZIP", r.status_code == 200 and r.content[:2] == b"PK", str(r.status_code))

    # ── frontend servido ─────────────────────────────────────────────
    for ruta in ("/", "/manifest.webmanifest", "/sw.js", "/static/styles.css",
                 "/static/js/app.js", "/static/icono-192.png"):
        r = c.get(ruta)
        check(f"GET {ruta}", r.status_code == 200, str(r.status_code))

print()
if fallos:
    print(f"❌ {len(fallos)} FALLOS: {fallos}")
    print(f"   Datos de la prueba conservados en: {DATOS}")
    sys.exit(1)

shutil.rmtree(DATOS, ignore_errors=True)
print("✅ Todas las comprobaciones pasan")
