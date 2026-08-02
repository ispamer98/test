"""
Capa de datos. SQLite, un único fichero, sin dependencias externas.

Las tablas de negocio se crean a partir de app/schema.py, de modo que añadir un
campo nuevo allí basta para que aparezca en la BD, la API y el formulario.
La migración es aditiva: al arrancar se comparan las columnas reales con las
declaradas y se hace ALTER TABLE ADD COLUMN de las que falten. Nunca se borran
columnas, así que actualizar la app jamás destruye datos.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .schema import ENTITIES, Entity

_local = threading.local()

DATA_DIR = Path(os.environ.get("OBRASEC_DATA", Path.home() / "ObraSec"))
DB_PATH = DATA_DIR / "obrasec.db"
FILES_DIR = DATA_DIR / "archivos"
TEMPLATES_DIR = DATA_DIR / "plantillas"
BACKUP_DIR = DATA_DIR / "backups"

# Tablas auxiliares que no salen del registro de entidades.
EXTRA_TABLES = """
CREATE TABLE IF NOT EXISTS adjuntos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id       INTEGER,
    entidad       TEXT NOT NULL,
    registro_id   INTEGER,
    nombre        TEXT NOT NULL,
    ruta          TEXT NOT NULL,
    mime          TEXT,
    tamano        INTEGER,
    categoria     TEXT,
    descripcion   TEXT,
    lat           REAL,
    lon           REAL,
    creado        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_adj ON adjuntos(entidad, registro_id);
CREATE INDEX IF NOT EXISTS ix_adj_obra ON adjuntos(obra_id);

CREATE TABLE IF NOT EXISTS plantillas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    tipo          TEXT NOT NULL DEFAULT 'docx',
    ruta          TEXT NOT NULL,
    descripcion   TEXT,
    campos        TEXT,
    creado        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ajustes (
    clave         TEXT PRIMARY KEY,
    valor         TEXT
);

CREATE TABLE IF NOT EXISTS catalogo_extra (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    catalogo      TEXT NOT NULL,
    valor         TEXT NOT NULL,
    UNIQUE(catalogo, valor)
);

CREATE TABLE IF NOT EXISTS log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha         TEXT NOT NULL,
    usuario       TEXT,
    accion        TEXT NOT NULL,
    entidad       TEXT,
    registro_id   INTEGER,
    obra_id       INTEGER,
    detalle       TEXT
);
CREATE INDEX IF NOT EXISTS ix_log_fecha ON log(fecha DESC);

CREATE TABLE IF NOT EXISTS sesiones (
    token         TEXT PRIMARY KEY,
    usuario       TEXT,
    creado        TEXT NOT NULL,
    expira        TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def conn() -> sqlite3.Connection:
    """Conexión por hilo. FastAPI usa un pool de hilos, así que no se comparte."""
    c = getattr(_local, "conn", None)
    if c is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(DB_PATH, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=5000")
        _local.conn = c
    return c


def _columns(table: str) -> set[str]:
    return {r["name"] for r in conn().execute(f"PRAGMA table_info({table})")}


def _table_exists(table: str) -> bool:
    r = conn().execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return r is not None


def _create_or_migrate(e: Entity) -> None:
    c = conn()
    base = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    if e.per_obra:
        base.append("obra_id INTEGER NOT NULL")
    cols = base + [f"{f.name} {f.sql_type()}" for f in e.fields]
    cols += ["creado TEXT", "modificado TEXT"]

    if not _table_exists(e.key):
        c.execute(f"CREATE TABLE {e.key} ({', '.join(cols)})")
        if e.per_obra:
            c.execute(f"CREATE INDEX ix_{e.key}_obra ON {e.key}(obra_id)")
    else:
        existing = _columns(e.key)
        for f in e.fields:
            if f.name not in existing:
                c.execute(f"ALTER TABLE {e.key} ADD COLUMN {f.name} {f.sql_type()}")
        for extra, typ in (("creado", "TEXT"), ("modificado", "TEXT")):
            if extra not in existing:
                c.execute(f"ALTER TABLE {e.key} ADD COLUMN {extra} {typ}")
        if e.per_obra and "obra_id" not in existing:
            c.execute(f"ALTER TABLE {e.key} ADD COLUMN obra_id INTEGER")
    c.commit()


def init() -> None:
    """Crea directorios, tablas y migra columnas nuevas. Idempotente."""
    for d in (DATA_DIR, FILES_DIR, TEMPLATES_DIR, BACKUP_DIR):
        d.mkdir(parents=True, exist_ok=True)
    c = conn()
    c.executescript(EXTRA_TABLES)
    for e in ENTITIES.values():
        _create_or_migrate(e)
    # Índices útiles para las búsquedas más frecuentes.
    c.execute("CREATE INDEX IF NOT EXISTS ix_disp_ip ON dispositivos(obra_id, ip)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_disp_serie ON dispositivos(num_serie)")
    c.commit()


# ─────────────────────────────────────────────────────────── ajustes (k/v)
def get_ajuste(clave: str, defecto: Any = None) -> Any:
    r = conn().execute("SELECT valor FROM ajustes WHERE clave=?", (clave,)).fetchone()
    if r is None or r["valor"] is None:
        return defecto
    try:
        return json.loads(r["valor"])
    except (json.JSONDecodeError, TypeError):
        return r["valor"]


def set_ajuste(clave: str, valor: Any) -> None:
    c = conn()
    c.execute(
        "INSERT INTO ajustes(clave, valor) VALUES(?,?) "
        "ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
        (clave, json.dumps(valor, ensure_ascii=False)),
    )
    c.commit()


def todos_ajustes() -> dict:
    return {r["clave"]: get_ajuste(r["clave"]) for r in conn().execute("SELECT clave FROM ajustes")}


# ───────────────────────────────────────────────────────────────── catálogos
def catalogo_extra(nombre: str) -> list[str]:
    return [
        r["valor"] for r in conn().execute(
            "SELECT valor FROM catalogo_extra WHERE catalogo=? ORDER BY valor", (nombre,)
        )
    ]


def add_catalogo(nombre: str, valor: str) -> None:
    valor = (valor or "").strip()
    if not valor:
        return
    c = conn()
    c.execute(
        "INSERT OR IGNORE INTO catalogo_extra(catalogo, valor) VALUES(?,?)", (nombre, valor)
    )
    c.commit()


def del_catalogo(nombre: str, valor: str) -> None:
    c = conn()
    c.execute("DELETE FROM catalogo_extra WHERE catalogo=? AND valor=?", (nombre, valor))
    c.commit()


# ─────────────────────────────────────────────────────────────────── CRUD
def _clean(e: Entity, data: dict) -> dict:
    """Filtra el payload a los campos declarados y normaliza tipos."""
    valid = {f.name: f for f in e.fields}
    out: dict[str, Any] = {}
    for k, v in data.items():
        f = valid.get(k)
        if f is None:
            continue
        if v == "" or v is None:
            out[k] = None
            continue
        if f.type in ("number", "money", "percent"):
            try:
                out[k] = float(str(v).replace(",", "."))
            except (TypeError, ValueError):
                out[k] = None
        elif f.type in ("int", "ref"):
            try:
                out[k] = int(float(v))
            except (TypeError, ValueError):
                out[k] = None
        elif f.type == "bool":
            out[k] = 1 if v in (True, 1, "1", "true", "True", "on", "Sí") else 0
        else:
            out[k] = str(v).strip()
    return out


def listar(
    key: str,
    obra_id: int | None = None,
    q: str | None = None,
    filtros: dict | None = None,
    limit: int = 5000,
    offset: int = 0,
) -> list[dict]:
    e = ENTITIES[key]
    where, params = [], []
    if e.per_obra and obra_id:
        where.append("obra_id = ?")
        params.append(obra_id)
    if q:
        texto = [f.name for f in e.fields if f.type in ("text", "textarea", "select", "ip", "mac", "email", "tel", "url")]
        if texto:
            where.append("(" + " OR ".join(f"COALESCE({c},'') LIKE ?" for c in texto) + ")")
            params += [f"%{q}%"] * len(texto)
    for k, v in (filtros or {}).items():
        if any(f.name == k for f in e.fields) and v not in (None, ""):
            where.append(f"{k} = ?")
            params.append(v)
    sql = f"SELECT * FROM {key}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {e.order_by} LIMIT ? OFFSET ?"
    params += [limit, offset]
    return [dict(r) for r in conn().execute(sql, params)]


def obtener(key: str, rid: int) -> dict | None:
    r = conn().execute(f"SELECT * FROM {key} WHERE id=?", (rid,)).fetchone()
    return dict(r) if r else None


def crear(key: str, data: dict, obra_id: int | None = None, usuario: str | None = None) -> dict:
    e = ENTITIES[key]
    vals = _clean(e, data)
    for f in e.fields:
        if f.name not in vals and f.default is not None:
            vals[f.name] = f.default
    if e.per_obra:
        vals["obra_id"] = obra_id or data.get("obra_id")
    vals["creado"] = now()
    vals["modificado"] = now()
    cols = ", ".join(vals)
    ph = ", ".join("?" for _ in vals)
    c = conn()
    cur = c.execute(f"INSERT INTO {key} ({cols}) VALUES ({ph})", list(vals.values()))
    c.commit()
    rid = cur.lastrowid
    registrar(usuario, "crear", key, rid, vals.get("obra_id"))
    return obtener(key, rid)


def actualizar(key: str, rid: int, data: dict, usuario: str | None = None) -> dict | None:
    e = ENTITIES[key]
    vals = _clean(e, data)
    if not vals:
        return obtener(key, rid)
    vals["modificado"] = now()
    sets = ", ".join(f"{k}=?" for k in vals)
    c = conn()
    c.execute(f"UPDATE {key} SET {sets} WHERE id=?", list(vals.values()) + [rid])
    c.commit()
    reg = obtener(key, rid)
    registrar(usuario, "editar", key, rid, (reg or {}).get("obra_id"))
    return reg


def borrar(key: str, rid: int, usuario: str | None = None) -> bool:
    reg = obtener(key, rid)
    c = conn()
    c.execute(f"DELETE FROM {key} WHERE id=?", (rid,))
    c.execute("DELETE FROM adjuntos WHERE entidad=? AND registro_id=?", (key, rid))
    c.commit()
    registrar(usuario, "borrar", key, rid, (reg or {}).get("obra_id"))
    return True


def contar(key: str, obra_id: int | None = None, **filtros) -> int:
    e = ENTITIES[key]
    where, params = [], []
    if e.per_obra and obra_id:
        where.append("obra_id=?")
        params.append(obra_id)
    for k, v in filtros.items():
        where.append(f"{k}=?")
        params.append(v)
    sql = f"SELECT COUNT(*) n FROM {key}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    return conn().execute(sql, params).fetchone()["n"]


def suma(key: str, campo: str, obra_id: int | None = None, **filtros) -> float:
    e = ENTITIES[key]
    where, params = [], []
    if e.per_obra and obra_id:
        where.append("obra_id=?")
        params.append(obra_id)
    for k, v in filtros.items():
        where.append(f"{k}=?")
        params.append(v)
    sql = f"SELECT COALESCE(SUM({campo}),0) s FROM {key}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    return float(conn().execute(sql, params).fetchone()["s"])


def query(sql: str, params: Iterable = ()) -> list[dict]:
    return [dict(r) for r in conn().execute(sql, list(params))]


# ───────────────────────────────────────────────────────────────── auditoría
def registrar(usuario: str | None, accion: str, entidad: str | None = None,
              rid: int | None = None, obra_id: int | None = None,
              detalle: str | None = None) -> None:
    c = conn()
    c.execute(
        "INSERT INTO log(fecha, usuario, accion, entidad, registro_id, obra_id, detalle) "
        "VALUES(?,?,?,?,?,?,?)",
        (now(), usuario, accion, entidad, rid, obra_id, detalle),
    )
    c.commit()


# ───────────────────────────────────────────────────────────────── adjuntos
def add_adjunto(entidad: str, registro_id: int | None, nombre: str, ruta: str,
                mime: str = "", tamano: int = 0, obra_id: int | None = None,
                categoria: str = "", descripcion: str = "",
                lat: float | None = None, lon: float | None = None) -> dict:
    c = conn()
    cur = c.execute(
        "INSERT INTO adjuntos(obra_id, entidad, registro_id, nombre, ruta, mime, tamano,"
        " categoria, descripcion, lat, lon, creado) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (obra_id, entidad, registro_id, nombre, ruta, mime, tamano, categoria,
         descripcion, lat, lon, now()),
    )
    c.commit()
    r = c.execute("SELECT * FROM adjuntos WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(r)


def adjuntos_de(entidad: str, registro_id: int) -> list[dict]:
    return query(
        "SELECT * FROM adjuntos WHERE entidad=? AND registro_id=? ORDER BY id DESC",
        (entidad, registro_id),
    )


def adjuntos_obra(obra_id: int, categoria: str | None = None) -> list[dict]:
    if categoria:
        return query(
            "SELECT * FROM adjuntos WHERE obra_id=? AND categoria=? ORDER BY id DESC",
            (obra_id, categoria),
        )
    return query("SELECT * FROM adjuntos WHERE obra_id=? ORDER BY id DESC", (obra_id,))


def borrar_adjunto(aid: int) -> bool:
    c = conn()
    r = c.execute("SELECT ruta FROM adjuntos WHERE id=?", (aid,)).fetchone()
    if r:
        try:
            Path(r["ruta"]).unlink(missing_ok=True)
        except OSError:
            pass
    c.execute("DELETE FROM adjuntos WHERE id=?", (aid,))
    c.commit()
    return True
