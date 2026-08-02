"""
Inteligencia artificial de obra (Claude).

Tres capacidades:
  1. `analizar_etiqueta`  — foto de la etiqueta de un equipo -> ficha de
     dispositivo lista para el inventario (S/N, MAC, modelo, marca, tipo…).
  2. `analizar_albaran`   — foto de un albarán -> líneas de material.
  3. `asistente`          — pregunta en lenguaje natural sobre el estado de la
     obra, respondida con los datos reales de la base.

La clave de API se guarda en Ajustes (tabla `ajustes`, clave `anthropic_api_key`)
o en la variable de entorno ANTHROPIC_API_KEY. Sin clave, el resto de la
aplicación funciona con normalidad: sólo se desactivan estas tres funciones.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

from .. import db

MODELO = "claude-opus-5"

# ─────────────────────────────────────────────────────── esquemas de salida
ESQUEMA_DISPOSITIVO = {
    "type": "object",
    "properties": {
        "encontrado": {
            "type": "boolean",
            "description": "true si la imagen contiene una etiqueta o equipo identificable",
        },
        "categoria": {
            "type": "string",
            "description": "Familia del equipo",
            "enum": ["CCTV", "Intrusión", "Control de Accesos", "Megafonía/PA",
                     "Detección de Incendios", "Redes y Cableado", "Alimentación/SAI",
                     "Interfonía", "Domótica/BMS", "Otros"],
        },
        "tipo": {"type": "string", "description": "Tipo concreto, ej. 'Cámara IP Bullet', 'Switch PoE', 'Detector Volumétrico PIR'"},
        "marca": {"type": "string", "description": "Fabricante. Cadena vacía si no se ve."},
        "modelo": {"type": "string", "description": "Modelo exacto tal y como aparece impreso."},
        "num_serie": {"type": "string", "description": "Número de serie (S/N, SN, Serial). Cadena vacía si no se ve."},
        "mac": {"type": "string", "description": "MAC en formato AA:BB:CC:DD:EE:FF. Vacío si no aparece."},
        "part_number": {"type": "string", "description": "Part number / P/N / referencia de fabricante."},
        "firmware": {"type": "string", "description": "Versión de firmware si aparece."},
        "poe": {"type": "string", "description": "Alimentación indicada en la etiqueta, ej. 'PoE (802.3af)', '12V DC'."},
        "resolucion": {"type": "string", "description": "Resolución o capacidad si aparece (ej. '4MP', '8 canales', '2TB')."},
        "consumo_w": {"type": "string", "description": "Consumo en vatios, sólo el número."},
        "otros_datos": {"type": "string", "description": "Cualquier otro dato legible relevante."},
        "texto_leido": {"type": "string", "description": "Transcripción literal de todo el texto visible en la etiqueta."},
        "confianza": {
            "type": "string",
            "enum": ["alta", "media", "baja"],
            "description": "Confianza en la lectura. 'baja' si la foto está borrosa o incompleta.",
        },
        "aviso": {"type": "string", "description": "Advertencia para el usuario si algo no se lee bien o hay ambigüedad."},
    },
    "required": ["encontrado", "categoria", "tipo", "marca", "modelo", "num_serie",
                 "mac", "part_number", "firmware", "poe", "resolucion", "consumo_w",
                 "otros_datos", "texto_leido", "confianza", "aviso"],
    "additionalProperties": False,
}

ESQUEMA_ALBARAN = {
    "type": "object",
    "properties": {
        "proveedor": {"type": "string"},
        "numero_albaran": {"type": "string"},
        "fecha": {"type": "string", "description": "Fecha en formato AAAA-MM-DD, vacío si no se lee."},
        "lineas": {
            "type": "array",
            "description": "Una entrada por línea de material del albarán.",
            "items": {
                "type": "object",
                "properties": {
                    "material": {"type": "string"},
                    "codigo": {"type": "string"},
                    "cantidad": {"type": "number"},
                    "unidad": {"type": "string"},
                    "precio": {"type": "number", "description": "Precio unitario, 0 si no aparece."},
                    "categoria": {
                        "type": "string",
                        "enum": ["Cableado", "Fibra Óptica", "Canalización", "Conectores/Rack",
                                 "CCTV", "Intrusión", "Control de Accesos", "Redes",
                                 "Electricidad", "Ferretería", "Soportería", "Señalización",
                                 "EPIs", "Otros"],
                    },
                },
                "required": ["material", "codigo", "cantidad", "unidad", "precio", "categoria"],
                "additionalProperties": False,
            },
        },
        "aviso": {"type": "string"},
    },
    "required": ["proveedor", "numero_albaran", "fecha", "lineas", "aviso"],
    "additionalProperties": False,
}

PROMPT_ETIQUETA = """Eres el jefe de obra de una empresa de instalaciones de seguridad \
(CCTV, intrusión, control de accesos) en naves logísticas. Estás dando de alta \
material en el inventario de instalación a partir de la foto de la etiqueta del equipo.

Extrae los datos de la etiqueta que ves en la imagen.

Reglas:
- Transcribe EXACTAMENTE lo impreso. No inventes ni completes datos que no veas.
- Si un dato no aparece o no se lee, devuelve cadena vacía. Nunca lo deduzcas.
- Cuidado con los caracteres que se confunden: 0/O, 1/I/l, 5/S, 8/B, 2/Z. Si la
  foto no permite distinguirlos con seguridad, marca confianza "baja" y dilo en
  el aviso indicando qué carácter es dudoso.
- El número de serie suele ir junto a S/N, SN, Serial No., Serie o un código de
  barras. El part number junto a P/N, Model, Ref.
- La MAC son 12 dígitos hexadecimales; normalízala a AA:BB:CC:DD:EE:FF en mayúsculas.
- Deduce `categoria` y `tipo` del aspecto del equipo y del modelo, aunque la
  etiqueta no lo diga literalmente: para eso tienes el criterio de un técnico.
- `texto_leido` debe contener todo el texto visible, aunque no lo uses.
"""

PROMPT_ALBARAN = """Eres el jefe de obra recepcionando material en una obra de \
instalaciones de seguridad. Extrae las líneas de material del albarán fotografiado.

Reglas:
- Una entrada por línea de producto. Transcribe la descripción tal cual.
- Si no se lee la cantidad de una línea, pon 0 y avísalo.
- No inventes precios: si el albarán no los trae, pon 0.
- Clasifica cada línea en la categoría más razonable según tu criterio técnico.
"""


class IAError(RuntimeError):
    pass


def api_key() -> str | None:
    return db.get_ajuste("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")


def disponible() -> bool:
    if not api_key():
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def _cliente():
    key = api_key()
    if not key:
        raise IAError(
            "No hay clave de API configurada. Ve a Ajustes › Inteligencia artificial "
            "y pega tu clave de Anthropic (empieza por sk-ant-)."
        )
    try:
        import anthropic
    except ImportError as exc:
        raise IAError(
            "Falta el paquete 'anthropic'. Instálalo con: pip install anthropic"
        ) from exc
    return anthropic.Anthropic(api_key=key)


def _mime(nombre: str) -> str:
    n = nombre.lower()
    if n.endswith(".png"):
        return "image/png"
    if n.endswith(".webp"):
        return "image/webp"
    if n.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


def _json_respuesta(resp) -> dict:
    texto = next((b.text for b in resp.content if b.type == "text"), "")
    if not texto:
        raise IAError("La IA no devolvió contenido. Prueba con otra foto.")
    return json.loads(texto)


def _extraer(imagenes: list[tuple[bytes, str]], prompt: str, esquema: dict,
             extra: str = "") -> dict:
    cliente = _cliente()
    contenido: list[dict[str, Any]] = []
    for datos, nombre in imagenes:
        contenido.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _mime(nombre),
                "data": base64.standard_b64encode(datos).decode("utf-8"),
            },
        })
    contenido.append({"type": "text", "text": prompt + ("\n\n" + extra if extra else "")})

    resp = cliente.messages.create(
        model=MODELO,
        max_tokens=8000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": esquema}},
        messages=[{"role": "user", "content": contenido}],
    )
    if resp.stop_reason == "refusal":
        raise IAError("La IA rechazó procesar esta imagen.")
    return _json_respuesta(resp)


# ──────────────────────────────────────────────────────────── etiquetas
_MAC_RE = re.compile(r"([0-9A-Fa-f]{2}[:\-]?){5}[0-9A-Fa-f]{2}")


def _normaliza_mac(valor: str) -> str:
    if not valor:
        return ""
    limpio = re.sub(r"[^0-9A-Fa-f]", "", valor)
    if len(limpio) != 12:
        return valor.strip().upper()
    return ":".join(limpio[i:i + 2] for i in range(0, 12, 2)).upper()


def analizar_etiqueta(imagenes: list[tuple[bytes, str]], contexto: str = "") -> dict:
    """Devuelve un dict con los campos de `dispositivos` listos para prerrellenar."""
    datos = _extraer(imagenes, PROMPT_ETIQUETA, ESQUEMA_DISPOSITIVO, contexto)

    if not datos.get("encontrado"):
        raise IAError(
            "No se ha reconocido ninguna etiqueta en la foto. Acércate más a la "
            "pegatina, evita reflejos y que quede enfocada."
        )

    mac = _normaliza_mac(datos.get("mac", ""))
    if not mac:
        m = _MAC_RE.search(datos.get("texto_leido", ""))
        if m:
            mac = _normaliza_mac(m.group(0))

    consumo = datos.get("consumo_w", "")
    try:
        consumo_val = float(re.sub(r"[^\d.,]", "", consumo).replace(",", ".")) if consumo else None
    except ValueError:
        consumo_val = None

    campos = {
        "categoria": datos.get("categoria") or "Otros",
        "tipo": datos.get("tipo") or "",
        "marca": datos.get("marca") or "",
        "modelo": datos.get("modelo") or "",
        "num_serie": datos.get("num_serie") or "",
        "mac": mac,
        "part_number": datos.get("part_number") or "",
        "firmware": datos.get("firmware") or "",
        "poe": datos.get("poe") or "",
        "resolucion": datos.get("resolucion") or "",
        "consumo_w": consumo_val,
    }
    notas = []
    if datos.get("otros_datos"):
        notas.append(datos["otros_datos"])
    if notas:
        campos["notas"] = " · ".join(notas)

    return {
        "campos": {k: v for k, v in campos.items() if v not in ("", None)},
        "confianza": datos.get("confianza", "media"),
        "aviso": datos.get("aviso", ""),
        "texto_leido": datos.get("texto_leido", ""),
    }


def analizar_albaran(imagenes: list[tuple[bytes, str]]) -> dict:
    return _extraer(imagenes, PROMPT_ALBARAN, ESQUEMA_ALBARAN)


# ──────────────────────────────────────────────────────────── asistente
PROMPT_ASISTENTE = """Eres el ayudante del jefe de obra de una empresa que instala \
sistemas de seguridad (CCTV, intrusión, control de accesos) en naves logísticas, \
normalmente como subcontratista de Telefónica y subcontratando a su vez la mano de obra.

Responde a la pregunta del usuario usando EXCLUSIVAMENTE los datos de la obra que \
se te facilitan más abajo. Habla como un jefe de obra con experiencia: directo, \
concreto y accionable.

Reglas:
- Si el dato no está en la información facilitada, dilo claramente. No inventes.
- Cita cifras exactas cuando las tengas.
- Si detectas un riesgo real para el plazo, el coste o la seguridad, señálalo aunque
  no te lo hayan preguntado.
- Sé breve. Nada de rodeos ni de repetir la pregunta.
"""


def asistente(pregunta: str, contexto: dict, historial: list[dict] | None = None) -> str:
    cliente = _cliente()
    ctx = json.dumps(contexto, ensure_ascii=False, indent=1, default=str)
    mensajes = list(historial or [])
    mensajes.append({
        "role": "user",
        "content": f"DATOS ACTUALES DE LA OBRA:\n```json\n{ctx}\n```\n\nPREGUNTA: {pregunta}",
    })
    resp = cliente.messages.create(
        model=MODELO,
        max_tokens=8000,
        system=PROMPT_ASISTENTE,
        output_config={"effort": "medium"},
        messages=mensajes,
    )
    if resp.stop_reason == "refusal":
        raise IAError("La IA no pudo responder a esta pregunta.")
    return "\n".join(b.text for b in resp.content if b.type == "text").strip()


PROMPT_REDACCION = """Eres el jefe de obra redactando documentación oficial de una \
obra de instalaciones de seguridad. Escribe en español de España, registro técnico \
y profesional, sin florituras. Usa exclusivamente los datos facilitados; si falta \
algún dato, escribe [PENDIENTE] en su lugar en vez de inventarlo."""


def redactar(instruccion: str, contexto: dict) -> str:
    """Redacta actas, resúmenes de visita o informes a partir de los datos de la obra."""
    cliente = _cliente()
    ctx = json.dumps(contexto, ensure_ascii=False, indent=1, default=str)
    resp = cliente.messages.create(
        model=MODELO,
        max_tokens=16000,
        system=PROMPT_REDACCION,
        output_config={"effort": "medium"},
        messages=[{
            "role": "user",
            "content": f"DATOS:\n```json\n{ctx}\n```\n\nENCARGO: {instruccion}",
        }],
    )
    if resp.stop_reason == "refusal":
        raise IAError("La IA no pudo redactar este documento.")
    return "\n".join(b.text for b in resp.content if b.type == "text").strip()
