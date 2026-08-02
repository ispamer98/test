#!/usr/bin/env python3
"""
ObraSec · arranque.

    python run.py

Levanta el servidor, abre el navegador y muestra la dirección y un código QR
para conectar el móvil o la tablet desde la misma red Wi-Fi.

Opciones útiles:
    python run.py --puerto 8080     usar otro puerto
    python run.py --sin-navegador   no abrir el navegador
    python run.py --publico         escuchar en todas las interfaces (requiere contraseña)
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).parent.resolve()
DEPENDENCIAS = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn[standard]"),
    ("openpyxl", "openpyxl"),
    ("multipart", "python-multipart"),
]
OPCIONALES = [
    ("docx", "python-docx", "informes en Word"),
    ("docxtpl", "docxtpl", "plantillas de Word propias"),
    ("anthropic", "anthropic", "funciones de inteligencia artificial"),
]


def _falta(modulo: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(modulo) is None


def comprobar_dependencias(instalar: bool = True) -> None:
    faltan = [pip for mod, pip in DEPENDENCIAS if _falta(mod)]
    if faltan:
        if not instalar:
            print(f"Faltan dependencias: {', '.join(faltan)}")
            print(f"Instálalas con:  {sys.executable} -m pip install {' '.join(faltan)}")
            sys.exit(1)
        print("Instalando lo necesario (solo la primera vez)…\n")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *faltan]
        )
        if r.returncode != 0:
            print("\nNo se han podido instalar las dependencias.")
            print(f"Prueba manualmente:  {sys.executable} -m pip install {' '.join(faltan)}")
            sys.exit(1)
        print()

    ausentes = [(pip, para) for mod, pip, para in OPCIONALES if _falta(mod)]
    if ausentes:
        print("Extras no instalados (la app funciona igual):")
        for pip, para in ausentes:
            print(f"  · {pip:<14} → {para}")
        print(f"  Instalar todo:  {sys.executable} -m pip install " +
              " ".join(p for p, _ in ausentes))
        print()


def ip_local() -> str:
    """IP de esta máquina en la red local, para conectar el móvil."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        s.close()


def puerto_libre(inicio: int) -> int:
    for p in range(inicio, inicio + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return inicio


def qr_consola(texto: str) -> str | None:
    try:
        import qrcode
    except ImportError:
        return None
    try:
        qr = qrcode.QRCode(border=1, box_size=1)
        qr.add_data(texto)
        qr.make(fit=True)
        m = qr.get_matrix()
        # Dos filas por línea usando medios bloques: el QR cabe en la consola.
        lineas = []
        for y in range(0, len(m), 2):
            fila = ""
            for x in range(len(m[0])):
                arriba = m[y][x]
                abajo = m[y + 1][x] if y + 1 < len(m) else False
                fila += "█" if arriba and abajo else "▀" if arriba else "▄" if abajo else " "
            lineas.append(fila)
        return "\n".join(lineas)
    except Exception:
        return None


def banner(url_local: str, url_red: str, publico: bool) -> None:
    ancho = 66
    print("\n" + "═" * ancho)
    print("  🏗️  OBRASEC · Gestor integral de obra".ljust(ancho))
    print("      Seguridad · CCTV · Intrusión · Control de accesos".ljust(ancho))
    print("═" * ancho)
    print(f"\n  En este ordenador:   {url_local}")
    if url_red:
        print(f"  Móvil y tablet:      {url_red}")
        print("                       (misma red Wi-Fi que este ordenador)")
    if publico:
        print("\n  ⚠  Modo público: accesible desde fuera. Usa contraseña.")

    qr = qr_consola(url_red or url_local)
    if qr:
        print("\n  Escanea con la cámara del móvil:\n")
        for linea in qr.splitlines():
            print("   " + linea)
    else:
        print("\n  (instala 'qrcode' para ver un QR aquí: pip install qrcode)")

    print("\n  📱 En el iPhone: abre la dirección en Safari, pulsa Compartir")
    print("     y elige «Añadir a pantalla de inicio». Quedará como una app.")
    print("\n  Para cerrar: Ctrl+C")
    print("═" * ancho + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="ObraSec · gestor de obra")
    p.add_argument("--puerto", type=int, default=8321)
    p.add_argument("--host", default=None)
    p.add_argument("--sin-navegador", action="store_true")
    p.add_argument("--publico", action="store_true",
                   help="escuchar en todas las interfaces (exige contraseña)")
    p.add_argument("--sin-instalar", action="store_true",
                   help="no instalar dependencias automáticamente")
    p.add_argument("--datos", default=None, help="carpeta donde guardar los datos")
    args = p.parse_args()

    comprobar_dependencias(instalar=not args.sin_instalar)

    if args.datos:
        os.environ["OBRASEC_DATA"] = str(Path(args.datos).resolve())
    if args.publico:
        os.environ["OBRASEC_PUBLIC"] = "1"

    sys.path.insert(0, str(RAIZ))
    puerto = puerto_libre(args.puerto)
    host = args.host or ("0.0.0.0" if args.publico else "0.0.0.0")

    url_local = f"http://localhost:{puerto}"
    ip = ip_local()
    url_red = f"http://{ip}:{puerto}" if ip and not ip.startswith("127.") else ""

    banner(url_local, url_red, args.publico)

    if not args.sin_navegador:
        threading.Timer(1.4, lambda: webbrowser.open(url_local)).start()

    import uvicorn
    try:
        uvicorn.run("app.main:app", host=host, port=puerto, log_level="warning",
                    access_log=False)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n  ObraSec cerrado. Tus datos siguen guardados.\n")


if __name__ == "__main__":
    main()
