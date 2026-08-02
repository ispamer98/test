"""
Pruebas de seguridad.

Comprueban las defensas que importan cuando la aplicación se publica en
internet: que un archivo subido no puede escaparse del directorio de datos,
que las consultas van parametrizadas, que la clave de la API nunca vuelve
entera y que sin sesión no se lee nada.

    python tests/test_seguridad.py
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = Path(tempfile.mkdtemp(prefix="obrasec_sec_"))
os.environ["OBRASEC_DATA"] = str(DATOS)
sys.path.insert(0, str(RAIZ))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, db  # noqa: E402
from app.main import app  # noqa: E402

fallos: list[str] = []


def check(nombre: str, condicion: bool, extra: str = "") -> None:
    print(("  OK    " if condicion else "  FALLO ") + nombre + (f"  {extra}" if not condicion else ""))
    if not condicion:
        fallos.append(nombre)


# ── Sin contraseña configurada ────────────────────────────────────────────
with TestClient(app) as c:
    obra = c.post("/api/e/obras", json={"nombre": "Obra de prueba", "estado": "En curso"}).json()

    # Un nombre de archivo con ../ no debe escribir fuera del directorio de datos.
    r = c.post(
        "/api/adjuntos",
        files={"archivo": ("../../../../evil.txt", b"contenido", "text/plain")},
        data={"entidad": "obras", "obra_id": str(obra["id"])},
    )
    ruta = Path(r.json()["ruta"]).resolve()
    check("la subida no escapa del directorio de datos", str(DATOS.resolve()) in str(ruta), str(ruta))
    check("el nombre de archivo se sanea", ".." not in ruta.name, ruta.name)

    # El nombre de entidad viene del registro, nunca del usuario.
    r = c.get("/api/e/obras;DROP TABLE obras")
    check("entidad desconocida rechazada", r.status_code == 404, str(r.status_code))
    check("la tabla sigue existiendo", db.contar("obras") == 1)

    # La búsqueda usa parámetros, no concatenación.
    r = c.get(f"/api/buscar?q=' OR '1'='1&obra={obra['id']}")
    check("la búsqueda va parametrizada", r.status_code == 200 and r.json() == [], r.text[:70])

    # Los secretos no salen por la API.
    completa = "sk-ant-CLAVE-SECRETA-COMPLETA-1234567890"
    db.set_ajuste("anthropic_api_key", completa)
    ajustes = c.get("/api/ajustes").json()
    check("la clave de API no se devuelve entera", completa not in str(ajustes))
    check("el hash de la contraseña no se expone", "password_hash" not in ajustes)

# ── Hash de contraseñas ───────────────────────────────────────────────────
h = auth.hash_password("contraseña-de-prueba")
check("hash PBKDF2 con sal", h.startswith("pbkdf2$240000$") and len(h) > 80)
check("acepta la contraseña correcta", auth.verificar_password("contraseña-de-prueba", h))
check("rechaza la incorrecta", not auth.verificar_password("otra distinta", h))
check("cada hash usa una sal nueva", auth.hash_password("x") != auth.hash_password("x"))

try:
    auth.set_password("123")
    check("rechaza contraseñas cortas", False, "aceptó una de 3 caracteres")
except ValueError:
    check("rechaza contraseñas cortas", True)

# ── Con contraseña configurada ────────────────────────────────────────────
auth.set_password("clave-larga-de-prueba")
with TestClient(app) as c:
    for ruta_protegida in ("/api/meta", "/api/e/obras", "/api/backup",
                           "/api/export/obra/1", "/api/ajustes", "/api/log"):
        r = c.get(ruta_protegida)
        check(f"401 sin sesión en {ruta_protegida}", r.status_code == 401, str(r.status_code))

    check("login con clave incorrecta rechazado",
          c.post("/api/login", json={"password": "incorrecta"}).status_code == 401)

    r = c.post("/api/login", json={"password": "clave-larga-de-prueba"})
    cookie = r.headers.get("set-cookie", "").lower()
    check("login correcto", r.status_code == 200, str(r.status_code))
    check("la cookie es httponly", "httponly" in cookie, cookie)
    check("la cookie es samesite=lax", "samesite=lax" in cookie, cookie)
    check("con sesión ya se puede leer", c.get("/api/meta").status_code == 200)

    c.post("/api/logout")
    check("tras cerrar sesión vuelve el 401", c.get("/api/meta").status_code == 401)

print()
if fallos:
    print(f"❌ {len(fallos)} FALLOS: {fallos}")
    print(f"   Datos de la prueba conservados en: {DATOS}")
    sys.exit(1)

shutil.rmtree(DATOS, ignore_errors=True)
print("✅ Revisión de seguridad superada")
