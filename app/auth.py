"""
Autenticación por contraseña única.

En local (`python run.py`) la app arranca sin contraseña: es tu ordenador.
En cuanto se publica en internet — por ejemplo en obra.tudominio.com — hay que
poner contraseña, y la app se niega a arrancar en modo público sin ella.

Se usa PBKDF2-SHA256 de la biblioteca estándar: sin dependencias extra y
suficientemente sólido para un único usuario.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from . import db

ITERACIONES = 240_000
DURACION_SESION = timedelta(days=30)


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERACIONES)
    return f"pbkdf2${ITERACIONES}${salt}${dk.hex()}"


def verificar_password(password: str, almacenado: str) -> bool:
    try:
        algo, iteraciones, salt, digest = almacenado.split("$")
        if algo != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iteraciones))
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, AttributeError):
        return False


def password_configurada() -> bool:
    return bool(db.get_ajuste("password_hash") or os.environ.get("OBRASEC_PASSWORD"))


def set_password(password: str) -> None:
    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    db.set_ajuste("password_hash", hash_password(password))
    db.query("DELETE FROM sesiones")
    db.conn().commit()


def quitar_password() -> None:
    db.set_ajuste("password_hash", None)
    db.conn().commit()


def comprobar(password: str) -> bool:
    guardado = db.get_ajuste("password_hash")
    if guardado:
        return verificar_password(password, guardado)
    env = os.environ.get("OBRASEC_PASSWORD")
    return bool(env) and hmac.compare_digest(password, env)


def crear_sesion(usuario: str = "jefe") -> str:
    token = secrets.token_urlsafe(32)
    ahora = datetime.now(timezone.utc)
    c = db.conn()
    c.execute(
        "INSERT INTO sesiones(token, usuario, creado, expira) VALUES(?,?,?,?)",
        (token, usuario, ahora.isoformat(), (ahora + DURACION_SESION).isoformat()),
    )
    c.execute("DELETE FROM sesiones WHERE expira < ?", (ahora.isoformat(),))
    c.commit()
    return token


def usuario_de(token: str | None) -> str | None:
    if not token:
        return None
    r = db.conn().execute(
        "SELECT usuario, expira FROM sesiones WHERE token=?", (token,)
    ).fetchone()
    if not r:
        return None
    try:
        if datetime.fromisoformat(r["expira"]) < datetime.now(timezone.utc):
            cerrar_sesion(token)
            return None
    except ValueError:
        return None
    return r["usuario"]


def cerrar_sesion(token: str | None) -> None:
    if not token:
        return
    c = db.conn()
    c.execute("DELETE FROM sesiones WHERE token=?", (token,))
    c.commit()
