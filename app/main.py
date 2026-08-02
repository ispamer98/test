"""
ObraSec · Gestor integral de obra para instalaciones de seguridad.

API + servidor de la aplicación web (PWA). Un único proceso Python sirve tanto
los datos como la interfaz, de modo que funciona igual en el PC, en la tablet y
en el iPhone: basta con abrir la dirección y añadirla a la pantalla de inicio.
"""
from __future__ import annotations

import io
import mimetypes
import os
import shutil
import unicodedata
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import auth, catalogs, db
from .schema import ENTITIES, MENU, entity
from .services import ai, exporter, importer, kpis, reports

WEB = Path(__file__).parent / "web"
VERSION = "1.0.0"

app = FastAPI(title="ObraSec", version=VERSION, docs_url="/api/docs", redoc_url=None)


@app.on_event("startup")
def _arranque() -> None:
    db.init()
    if os.environ.get("OBRASEC_PUBLIC") == "1" and not auth.password_configurada():
        raise RuntimeError(
            "OBRASEC_PUBLIC=1 pero no hay contraseña. Define OBRASEC_PASSWORD "
            "o configúrala en Ajustes antes de exponer la app a internet."
        )


# ═══════════════════════════════════════════════════════════════ seguridad
def sesion(request: Request) -> str:
    """Dependencia: devuelve el usuario o corta con 401."""
    if not auth.password_configurada():
        return "local"
    usuario = auth.usuario_de(request.cookies.get("obrasec"))
    if not usuario:
        raise HTTPException(401, "Sesión no iniciada")
    return usuario


@app.post("/api/login")
async def login(request: Request):
    datos = await request.json()
    if not auth.password_configurada():
        return {"ok": True, "sin_password": True}
    if not auth.comprobar(str(datos.get("password", ""))):
        db.registrar(None, "login_fallido", detalle=request.client.host if request.client else "")
        raise HTTPException(401, "Contraseña incorrecta")
    token = auth.crear_sesion()
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        "obrasec", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30,
        secure=os.environ.get("OBRASEC_PUBLIC") == "1",
    )
    db.registrar("jefe", "login")
    return resp


@app.post("/api/logout")
def logout(request: Request):
    auth.cerrar_sesion(request.cookies.get("obrasec"))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("obrasec")
    return resp


@app.get("/api/estado")
def estado(request: Request):
    autenticado = (not auth.password_configurada()) or bool(
        auth.usuario_de(request.cookies.get("obrasec"))
    )
    return {
        "version": VERSION,
        "requiere_password": auth.password_configurada(),
        "autenticado": autenticado,
        "ia": ai.disponible(),
    }


# ═══════════════════════════════════════════════════════════ metadatos
def _catalogo_completo(nombre: str) -> list[str]:
    base = catalogs.catalogo(nombre)
    extra = [v for v in db.catalogo_extra(nombre) if v not in base]
    return base + extra


@app.get("/api/meta")
def meta(usuario: str = Depends(sesion)):
    """Esquema completo: el frontend construye toda la interfaz a partir de esto."""
    cats = {n: _catalogo_completo(n) for n in catalogs.CATALOGOS}
    cats["_clientes"] = catalogs.CLIENTES_SUGERIDOS + [
        v for v in db.catalogo_extra("_clientes") if v not in catalogs.CLIENTES_SUGERIDOS
    ]
    zonas_base = catalogs.ZONAS_SUGERIDAS
    cats["_zonas"] = zonas_base + [
        v for v in db.catalogo_extra("_zonas") if v not in zonas_base
    ]
    return {
        "version": VERSION,
        "entidades": {k: e.to_dict() for k, e in ENTITIES.items()},
        "menu": MENU,
        "catalogos": cats,
        "ia": ai.disponible(),
        "carpetas": catalogs.ESTRUCTURA_CARPETAS,
    }


# ═══════════════════════════════════════════════════════════════ CRUD
def _validar(key: str) -> None:
    if key not in ENTITIES:
        raise HTTPException(404, f"Entidad desconocida: {key}")


@app.get("/api/e/{key}")
def listar(key: str, obra: int | None = None, q: str | None = None,
           limit: int = 5000, offset: int = 0, usuario: str = Depends(sesion)):
    _validar(key)
    return db.listar(key, obra, q, limit=limit, offset=offset)


@app.get("/api/e/{key}/{rid}")
def obtener(key: str, rid: int, usuario: str = Depends(sesion)):
    _validar(key)
    reg = db.obtener(key, rid)
    if not reg:
        raise HTTPException(404, "Registro no encontrado")
    reg["_adjuntos"] = db.adjuntos_de(key, rid)
    return reg


@app.post("/api/e/{key}")
async def crear(key: str, request: Request, obra: int | None = None,
                usuario: str = Depends(sesion)):
    _validar(key)
    datos = await request.json()
    ent = entity(key)
    for f in ent.fields:
        if f.req and not datos.get(f.name):
            raise HTTPException(400, f"Falta el campo obligatorio: {f.label}")
    reg = db.crear(key, datos, obra_id=obra or datos.get("obra_id"), usuario=usuario)
    if key == "obras":
        _crear_carpetas(reg)
    return reg


@app.put("/api/e/{key}/{rid}")
async def actualizar(key: str, rid: int, request: Request, usuario: str = Depends(sesion)):
    _validar(key)
    datos = await request.json()
    reg = db.actualizar(key, rid, datos, usuario=usuario)
    if not reg:
        raise HTTPException(404, "Registro no encontrado")
    return reg


@app.delete("/api/e/{key}/{rid}")
def borrar(key: str, rid: int, usuario: str = Depends(sesion)):
    _validar(key)
    db.borrar(key, rid, usuario=usuario)
    return {"ok": True}


@app.post("/api/e/{key}/lote")
async def crear_lote(key: str, request: Request, obra: int | None = None,
                     usuario: str = Depends(sesion)):
    """Alta múltiple: útil para dar de alta 24 cámaras iguales de una vez."""
    _validar(key)
    cuerpo = await request.json()
    filas = cuerpo if isinstance(cuerpo, list) else cuerpo.get("filas", [])
    creados = [db.crear(key, f, obra_id=obra or f.get("obra_id"), usuario=usuario)
               for f in filas]
    return {"creados": len(creados), "registros": creados}


@app.post("/api/e/{key}/duplicar/{rid}")
def duplicar(key: str, rid: int, veces: int = 1, usuario: str = Depends(sesion)):
    _validar(key)
    origen = db.obtener(key, rid)
    if not origen:
        raise HTTPException(404, "Registro no encontrado")
    ent = entity(key)
    creados = []
    for i in range(max(1, min(veces, 200))):
        datos = {f.name: origen.get(f.name) for f in ent.fields}
        titulo = datos.get(ent.title_field)
        if isinstance(titulo, str) and titulo:
            datos[ent.title_field] = _siguiente_nombre(titulo, i + 1)
        for unico in ("num_serie", "mac", "ip"):
            if unico in datos:
                datos[unico] = None
        creados.append(db.crear(key, datos, obra_id=origen.get("obra_id"), usuario=usuario))
    return {"creados": len(creados), "registros": creados}


def _siguiente_nombre(titulo: str, offset: int) -> str:
    """CAM-MUELLE-01 -> CAM-MUELLE-02. Si no acaba en número, añade sufijo."""
    import re
    m = re.search(r"(\d+)\s*$", titulo)
    if not m:
        return f"{titulo} ({offset + 1})"
    numero = m.group(1)
    nuevo = str(int(numero) + offset).zfill(len(numero))
    return titulo[:m.start(1)] + nuevo


# ═══════════════════════════════════════════════════════ cuadro de mando
@app.get("/api/obras/{obra_id}/resumen")
def resumen(obra_id: int, usuario: str = Depends(sesion)):
    if not db.obtener("obras", obra_id):
        raise HTTPException(404, "Obra no encontrada")
    return kpis.resumen(obra_id)


@app.get("/api/obras/{obra_id}/gantt")
def gantt(obra_id: int, usuario: str = Depends(sesion)):
    return kpis.gantt(obra_id)


@app.get("/api/obras/{obra_id}/stock")
def stock(obra_id: int, usuario: str = Depends(sesion)):
    return kpis.stock(obra_id)


@app.get("/api/obras/{obra_id}/alertas")
def alertas(obra_id: int, usuario: str = Depends(sesion)):
    return kpis.alertas(obra_id)


@app.get("/api/panel")
def panel(usuario: str = Depends(sesion)):
    """Vista multi-obra: una línea por obra abierta con sus indicadores clave."""
    salida = []
    for o in db.listar("obras"):
        if o.get("estado") in ("Cancelada",):
            continue
        r = kpis.resumen(o["id"])
        criticas = sum(1 for a in r["alertas"] if a["severidad"] == "critica")
        salida.append({
            "obra": o,
            "avance": r["tareas"]["avance"],
            "retrasadas": r["tareas"]["retrasadas"],
            "dispositivos": r["dispositivos"]["total"],
            "instalados": r["dispositivos"]["instalados"],
            "margen_pct": r["economico"]["margen_pct"],
            "alertas": len(r["alertas"]),
            "criticas": criticas,
            "dias_restantes": r["plazo"]["dias_restantes"],
        })
    return salida


@app.get("/api/buscar")
def buscar(q: str, obra: int | None = None, usuario: str = Depends(sesion)):
    """Búsqueda global en todos los módulos de la obra."""
    if len(q.strip()) < 2:
        return []
    salida = []
    for key, ent in ENTITIES.items():
        filas = db.listar(key, obra if ent.per_obra else None, q=q, limit=25)
        for f in filas:
            salida.append({
                "entidad": key, "plural": ent.plural, "icono": ent.icon,
                "id": f["id"], "titulo": f.get(ent.title_field) or f"#{f['id']}",
                "estado": f.get("estado"), "obra_id": f.get("obra_id"),
            })
    return salida[:120]


# ═════════════════════════════════════════════════════ validaciones vivas
@app.get("/api/obras/{obra_id}/ip-libre")
def ip_libre(obra_id: int, ip: str, excluir: int | None = None,
             usuario: str = Depends(sesion)):
    """Comprueba si una IP ya está usada en la obra antes de guardar."""
    filas = db.query(
        "SELECT id, etiqueta FROM dispositivos WHERE obra_id=? AND ip=?", (obra_id, ip.strip())
    )
    ocupada = [f for f in filas if f["id"] != excluir]
    return {"libre": not ocupada, "usada_por": [f["etiqueta"] for f in ocupada]}


@app.get("/api/serie-existe")
def serie_existe(num_serie: str, excluir: int | None = None, usuario: str = Depends(sesion)):
    filas = db.query(
        "SELECT d.id, d.etiqueta, o.nombre obra FROM dispositivos d "
        "LEFT JOIN obras o ON o.id = d.obra_id WHERE d.num_serie = ?", (num_serie.strip(),)
    )
    otros = [f for f in filas if f["id"] != excluir]
    return {"existe": bool(otros), "registros": otros}


# ═══════════════════════════════════════════════════════════════ adjuntos
def _nombre_seguro(nombre: str) -> str:
    base = Path(nombre or "archivo").name
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    limpio = "".join(c for c in base if c.isalnum() or c in "._- ").strip()
    return limpio or "archivo"


def _descarga(nombre: str) -> dict[str, str]:
    """Cabecera Content-Disposition válida con nombres acentuados.

    Las cabeceras HTTP son latin-1: un nombre como «Inventario instalación.xlsx»
    revienta la respuesta. Se manda una versión ASCII como respaldo y la real
    codificada según RFC 5987, que es la que usan todos los navegadores actuales.
    """
    ascii_seguro = _nombre_seguro(nombre) or "descarga"
    utf8 = quote(nombre, safe="")
    return {
        "Content-Disposition": f"attachment; filename=\"{ascii_seguro}\"; filename*=UTF-8''{utf8}"
    }


@app.post("/api/adjuntos")
async def subir_adjunto(
    archivo: UploadFile = File(...),
    entidad: str = Form("obras"),
    registro_id: int | None = Form(None),
    obra_id: int | None = Form(None),
    categoria: str = Form(""),
    descripcion: str = Form(""),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    usuario: str = Depends(sesion),
):
    datos = await archivo.read()
    if len(datos) > 60 * 1024 * 1024:
        raise HTTPException(413, "El archivo supera los 60 MB")
    carpeta = db.FILES_DIR / str(obra_id or 0) / entidad
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = _nombre_seguro(archivo.filename or "archivo")
    destino = carpeta / f"{datetime.now():%Y%m%d%H%M%S}_{nombre}"
    destino.write_bytes(datos)
    return db.add_adjunto(
        entidad, registro_id, nombre, str(destino),
        archivo.content_type or mimetypes.guess_type(nombre)[0] or "",
        len(datos), obra_id, categoria, descripcion, lat, lon,
    )


@app.get("/api/adjuntos/{aid}/archivo")
def descargar_adjunto(aid: int, usuario: str = Depends(sesion)):
    r = db.query("SELECT * FROM adjuntos WHERE id=?", (aid,))
    if not r:
        raise HTTPException(404, "Adjunto no encontrado")
    ruta = Path(r[0]["ruta"])
    if not ruta.exists():
        raise HTTPException(404, "El archivo ya no está en disco")
    return FileResponse(ruta, filename=r[0]["nombre"], media_type=r[0]["mime"] or None)


@app.get("/api/adjuntos")
def listar_adjuntos(entidad: str | None = None, registro_id: int | None = None,
                    obra: int | None = None, usuario: str = Depends(sesion)):
    if entidad and registro_id:
        return db.adjuntos_de(entidad, registro_id)
    if obra:
        return db.adjuntos_obra(obra)
    return []


@app.delete("/api/adjuntos/{aid}")
def borrar_adjunto(aid: int, usuario: str = Depends(sesion)):
    db.borrar_adjunto(aid)
    return {"ok": True}


# ══════════════════════════════════════════════════════════ inteligencia
@app.post("/api/ia/etiqueta")
async def ia_etiqueta(archivos: list[UploadFile] = File(...), contexto: str = Form(""),
                      usuario: str = Depends(sesion)):
    """Foto de la etiqueta -> ficha de dispositivo prerrellenada."""
    imagenes = [(await f.read(), f.filename or "foto.jpg") for f in archivos[:4]]
    try:
        return ai.analizar_etiqueta(imagenes, contexto)
    except ai.IAError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Error al analizar la imagen: {exc}") from exc


@app.post("/api/ia/albaran")
async def ia_albaran(archivos: list[UploadFile] = File(...), usuario: str = Depends(sesion)):
    imagenes = [(await f.read(), f.filename or "foto.jpg") for f in archivos[:6]]
    try:
        return ai.analizar_albaran(imagenes)
    except ai.IAError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Error al analizar el albarán: {exc}") from exc


@app.post("/api/ia/preguntar")
async def ia_preguntar(request: Request, usuario: str = Depends(sesion)):
    cuerpo = await request.json()
    obra_id = int(cuerpo.get("obra_id") or 0)
    pregunta = str(cuerpo.get("pregunta", "")).strip()
    if not pregunta:
        raise HTTPException(400, "Falta la pregunta")
    if not obra_id:
        raise HTTPException(400, "Selecciona una obra primero")
    try:
        respuesta = ai.asistente(pregunta, kpis.contexto_ia(obra_id), cuerpo.get("historial"))
        return {"respuesta": respuesta}
    except ai.IAError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Error del asistente: {exc}") from exc


@app.post("/api/ia/redactar")
async def ia_redactar(request: Request, usuario: str = Depends(sesion)):
    cuerpo = await request.json()
    obra_id = int(cuerpo.get("obra_id") or 0)
    instruccion = str(cuerpo.get("instruccion", "")).strip()
    if not (obra_id and instruccion):
        raise HTTPException(400, "Faltan datos")
    try:
        return {"texto": ai.redactar(instruccion, kpis.contexto_ia(obra_id))}
    except ai.IAError as exc:
        raise HTTPException(400, str(exc)) from exc


# ══════════════════════════════════════════════════════════════ informes
@app.get("/api/plantillas")
def listar_plantillas(usuario: str = Depends(sesion)):
    return db.query("SELECT * FROM plantillas ORDER BY nombre")


@app.post("/api/plantillas")
async def subir_plantilla(archivo: UploadFile = File(...), nombre: str = Form(""),
                          descripcion: str = Form(""), usuario: str = Depends(sesion)):
    nombre_archivo = _nombre_seguro(archivo.filename or "plantilla.docx")
    if not nombre_archivo.lower().endswith((".docx", ".dotx")):
        raise HTTPException(400, "La plantilla debe ser un archivo .docx de Word")
    datos = await archivo.read()
    destino = db.TEMPLATES_DIR / f"{datetime.now():%Y%m%d%H%M%S}_{nombre_archivo}"
    destino.write_bytes(datos)
    c = db.conn()
    cur = c.execute(
        "INSERT INTO plantillas(nombre, tipo, ruta, descripcion, creado) VALUES(?,?,?,?,?)",
        (nombre or nombre_archivo, "docx", str(destino), descripcion, db.now()),
    )
    c.commit()
    return db.query("SELECT * FROM plantillas WHERE id=?", (cur.lastrowid,))[0]


@app.delete("/api/plantillas/{pid}")
def borrar_plantilla(pid: int, usuario: str = Depends(sesion)):
    r = db.query("SELECT ruta FROM plantillas WHERE id=?", (pid,))
    if r:
        Path(r[0]["ruta"]).unlink(missing_ok=True)
    c = db.conn()
    c.execute("DELETE FROM plantillas WHERE id=?", (pid,))
    c.commit()
    return {"ok": True}


@app.get("/api/plantillas/campos")
def campos_plantilla(usuario: str = Depends(sesion)):
    return reports.campos_disponibles()


@app.get("/api/informes/{obra_id}")
def generar_informe(obra_id: int, plantilla: int | None = None,
                    usuario: str = Depends(sesion)):
    if not db.obtener("obras", obra_id):
        raise HTTPException(404, "Obra no encontrada")
    try:
        if plantilla:
            r = db.query("SELECT * FROM plantillas WHERE id=?", (plantilla,))
            if not r:
                raise HTTPException(404, "Plantilla no encontrada")
            ruta = Path(r[0]["ruta"])
            if not ruta.exists():
                raise HTTPException(404, "El archivo de plantilla ya no existe")
            datos = reports.generar_docx(ruta, obra_id)
            nombre = f"{exporter.nombre_archivo(obra_id, _nombre_seguro(r[0]['nombre']).replace('.docx', ''))}.docx"
        else:
            datos = reports.informe_estandar(obra_id)
            nombre = f"{exporter.nombre_archivo(obra_id, 'Informe')}.docx"
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            500, f"No se pudo generar el informe. Revisa los marcadores de la plantilla. ({exc})"
        ) from exc
    db.registrar(usuario, "informe", None, None, obra_id, nombre)
    return Response(
        datos,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=_descarga(nombre),
    )


# ═══════════════════════════════════════════════════════════ exportación
@app.get("/api/export/obra/{obra_id}")
def export_obra(obra_id: int, usuario: str = Depends(sesion)):
    if not db.obtener("obras", obra_id):
        raise HTTPException(404, "Obra no encontrada")
    datos = exporter.libro_obra(obra_id)
    nombre = f"{exporter.nombre_archivo(obra_id, 'ControlObra')}.xlsx"
    return Response(
        datos,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_descarga(nombre),
    )


@app.get("/api/export/{key}")
def export_entidad(key: str, obra: int | None = None, usuario: str = Depends(sesion)):
    _validar(key)
    datos = exporter.libro_entidad(key, obra)
    nombre = f"{exporter.nombre_archivo(obra, ENTITIES[key].plural.replace(' ', ''))}.xlsx"
    return Response(
        datos,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_descarga(nombre),
    )


# ═══════════════════════════════════════════════════════════ importación
@app.post("/api/import/analizar")
async def import_analizar(archivo: UploadFile = File(...), usuario: str = Depends(sesion)):
    tmp = db.DATA_DIR / f".import_{datetime.now():%Y%m%d%H%M%S}_{_nombre_seguro(archivo.filename or 'libro.xlsx')}"
    tmp.write_bytes(await archivo.read())
    try:
        informe = importer.analizar(tmp)
        informe["ficha_obra"] = importer.datos_obra_desde_libro(tmp)
        informe["archivo"] = tmp.name
        return informe
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise HTTPException(400, f"No se pudo leer el archivo: {exc}") from exc


@app.post("/api/import/ejecutar")
async def import_ejecutar(request: Request, usuario: str = Depends(sesion)):
    cuerpo = await request.json()
    archivo = str(cuerpo.get("archivo", ""))
    obra_id = int(cuerpo.get("obra_id") or 0)
    if not archivo or not obra_id:
        raise HTTPException(400, "Faltan datos")
    ruta = db.DATA_DIR / Path(archivo).name
    if not ruta.exists() or not ruta.name.startswith(".import_"):
        raise HTTPException(404, "Archivo temporal no encontrado; vuelve a subirlo")
    try:
        resultado = importer.importar(ruta, obra_id, usuario, cuerpo.get("hojas"))
    finally:
        ruta.unlink(missing_ok=True)
    return resultado


# ═══════════════════════════════════════════════════════════════ ajustes
@app.get("/api/ajustes")
def get_ajustes(usuario: str = Depends(sesion)):
    todos = db.todos_ajustes()
    clave = todos.pop("anthropic_api_key", None)
    todos.pop("password_hash", None)
    todos["ia_configurada"] = bool(clave or os.environ.get("ANTHROPIC_API_KEY"))
    todos["ia_clave_parcial"] = (clave[:12] + "…" + clave[-4:]) if clave else ""
    todos["requiere_password"] = auth.password_configurada()
    todos["carpeta_datos"] = str(db.DATA_DIR)
    return todos


@app.post("/api/ajustes")
async def set_ajustes(request: Request, usuario: str = Depends(sesion)):
    datos = await request.json()
    for k, v in datos.items():
        if k in ("password_hash",):
            continue
        db.set_ajuste(k, v)
    return {"ok": True}


@app.post("/api/ajustes/password")
async def cambiar_password(request: Request, usuario: str = Depends(sesion)):
    datos = await request.json()
    nueva = str(datos.get("password", ""))
    if not nueva:
        auth.quitar_password()
        return {"ok": True, "password": False}
    try:
        auth.set_password(nueva)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "password": True}


@app.get("/api/catalogos/{nombre}")
def get_catalogo(nombre: str, usuario: str = Depends(sesion)):
    return _catalogo_completo(nombre)


@app.post("/api/catalogos/{nombre}")
async def add_catalogo(nombre: str, request: Request, usuario: str = Depends(sesion)):
    datos = await request.json()
    db.add_catalogo(nombre, str(datos.get("valor", "")))
    return _catalogo_completo(nombre)


@app.delete("/api/catalogos/{nombre}")
async def del_catalogo(nombre: str, valor: str, usuario: str = Depends(sesion)):
    db.del_catalogo(nombre, valor)
    return _catalogo_completo(nombre)


@app.get("/api/log")
def ver_log(obra: int | None = None, limit: int = 300, usuario: str = Depends(sesion)):
    if obra:
        return db.query(
            "SELECT * FROM log WHERE obra_id=? ORDER BY id DESC LIMIT ?", (obra, limit))
    return db.query("SELECT * FROM log ORDER BY id DESC LIMIT ?", (limit,))


# ════════════════════════════════════════════════════════ copia de seguridad
@app.get("/api/backup")
def backup(usuario: str = Depends(sesion)):
    """Descarga un ZIP con la base de datos, los archivos y las plantillas."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if db.DB_PATH.exists():
            z.write(db.DB_PATH, "obrasec.db")
        for carpeta, prefijo in ((db.FILES_DIR, "archivos"), (db.TEMPLATES_DIR, "plantillas")):
            for p in carpeta.rglob("*"):
                if p.is_file():
                    z.write(p, f"{prefijo}/{p.relative_to(carpeta)}")
    nombre = f"ObraSec_backup_{date.today():%Y%m%d}.zip"
    db.registrar(usuario, "backup")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


@app.post("/api/restore")
async def restore(archivo: UploadFile = File(...), usuario: str = Depends(sesion)):
    datos = await archivo.read()
    respaldo = db.BACKUP_DIR / f"antes_de_restaurar_{datetime.now():%Y%m%d%H%M%S}.db"
    if db.DB_PATH.exists():
        shutil.copy2(db.DB_PATH, respaldo)
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        nombres = z.namelist()
        if "obrasec.db" not in nombres:
            raise HTTPException(400, "El ZIP no contiene una base de datos de ObraSec")
        db.conn().close()
        db._local.conn = None
        db.DB_PATH.write_bytes(z.read("obrasec.db"))
        for n in nombres:
            if n.startswith(("archivos/", "plantillas/")) and not n.endswith("/"):
                base = db.FILES_DIR if n.startswith("archivos/") else db.TEMPLATES_DIR
                destino = base / n.split("/", 1)[1]
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(z.read(n))
    db.init()
    return {"ok": True, "respaldo_previo": str(respaldo)}


# ════════════════════════════════════════════════════════ carpetas de obra
def _crear_carpetas(obra: dict) -> None:
    """Crea en disco la estructura de carpetas de la obra, si se indicó una ruta."""
    ruta = (obra or {}).get("carpeta")
    if not ruta:
        return
    try:
        base = Path(ruta)
        base.mkdir(parents=True, exist_ok=True)
        for nombre, _ in catalogs.ESTRUCTURA_CARPETAS:
            (base / nombre).mkdir(exist_ok=True)
    except OSError:
        pass


@app.post("/api/obras/{obra_id}/carpetas")
def crear_carpetas(obra_id: int, usuario: str = Depends(sesion)):
    obra = db.obtener("obras", obra_id)
    if not obra:
        raise HTTPException(404, "Obra no encontrada")
    if not obra.get("carpeta"):
        raise HTTPException(400, "La obra no tiene definida una carpeta en disco")
    _crear_carpetas(obra)
    return {"ok": True, "carpeta": obra["carpeta"],
            "subcarpetas": [n for n, _ in catalogs.ESTRUCTURA_CARPETAS]}


# ══════════════════════════════════════════════════════════════ frontend
@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse({
        "name": "ObraSec · Gestor de Obra",
        "short_name": "ObraSec",
        "description": "Control integral de obras de instalaciones de seguridad",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "lang": "es-ES",
        "icons": [
            {"src": "/static/icono-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/icono-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/static/icono-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    ruta = WEB / "sw.js"
    return FileResponse(ruta, media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})


app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/", response_class=HTMLResponse)
@app.get("/{ruta:path}", response_class=HTMLResponse)
def spa(ruta: str = ""):
    """Todas las rutas devuelven la aplicación; el enrutado es del lado cliente."""
    if ruta.startswith(("api/", "static/")):
        raise HTTPException(404)
    return FileResponse(WEB / "index.html")
