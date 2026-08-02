#!/usr/bin/env python3
"""
Punto de entrada del ejecutable ObraSec.exe.

Se diferencia de run.py en dos cosas: no intenta instalar dependencias (ya van
dentro del ejecutable) y carga la aplicación como objeto en lugar de por su
ruta de importación, que es lo que espera PyInstaller.

Para uso normal desde el código fuente, usa `python run.py`.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

if getattr(sys, "frozen", False):
    # Dentro del ejecutable los módulos viven en la carpeta temporal _MEIPASS.
    sys.path.insert(0, sys._MEIPASS)  # type: ignore[attr-defined]
else:
    sys.path.insert(0, str(Path(__file__).parent.resolve()))

from run import banner, ip_local, puerto_libre  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="ObraSec · gestor de obra")
    p.add_argument("--puerto", type=int, default=8321)
    p.add_argument("--sin-navegador", action="store_true")
    p.add_argument("--publico", action="store_true")
    p.add_argument("--datos", default=None)
    args = p.parse_args()

    if args.datos:
        os.environ["OBRASEC_DATA"] = str(Path(args.datos).resolve())
    if args.publico:
        os.environ["OBRASEC_PUBLIC"] = "1"

    puerto = puerto_libre(args.puerto)
    url_local = f"http://localhost:{puerto}"
    ip = ip_local()
    url_red = f"http://{ip}:{puerto}" if ip and not ip.startswith("127.") else ""

    banner(url_local, url_red, args.publico)

    if not args.sin_navegador:
        threading.Timer(1.4, lambda: webbrowser.open(url_local)).start()

    import uvicorn
    from app.main import app

    try:
        uvicorn.run(app, host="0.0.0.0", port=puerto, log_level="warning", access_log=False)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n  ObraSec cerrado. Tus datos siguen guardados.\n")


if __name__ == "__main__":
    main()
