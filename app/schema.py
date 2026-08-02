"""
Registro de entidades.

Una sola definición por entidad genera:
  * la tabla SQLite (app/db.py)
  * los endpoints REST CRUD (app/main.py)
  * los formularios y tablas del frontend (GET /api/meta -> web/app.js)
  * las columnas de la exportación a Excel (app/services/exporter.py)

Tipos de campo admitidos:
  text textarea number int money percent date datetime bool
  select  -> requiere `cat` (nombre de catálogo) o `options`
  ref     -> requiere `ref` (nombre de entidad); se muestra como desplegable
  ip mac email tel url color
"""
from dataclasses import dataclass, field as dc_field
from typing import Any


@dataclass
class F:
    """Definición de un campo."""
    name: str
    label: str
    type: str = "text"
    cat: str | None = None            # catálogo para type=select
    options: list[str] | None = None  # opciones literales para type=select
    ref: str | None = None            # entidad referenciada para type=ref
    req: bool = False                 # obligatorio
    list: bool = False                # aparece en la vista de tabla
    group: str = "General"            # pestaña/sección del formulario
    help: str = ""
    default: Any = None
    width: int = 1                    # 1 = media fila, 2 = fila completa

    def sql_type(self) -> str:
        if self.type in ("number", "money", "percent"):
            return "REAL"
        if self.type in ("int", "bool"):
            return "INTEGER"
        if self.type == "ref":
            return "INTEGER"
        return "TEXT"

    def to_dict(self) -> dict:
        d = {
            "name": self.name, "label": self.label, "type": self.type,
            "req": self.req, "list": self.list, "group": self.group,
            "help": self.help, "width": self.width,
        }
        if self.cat:
            d["cat"] = self.cat
        if self.options:
            d["options"] = self.options
        if self.ref:
            d["ref"] = self.ref
        if self.default is not None:
            d["default"] = self.default
        return d


@dataclass
class Entity:
    """Definición de una entidad de negocio."""
    key: str                       # nombre de tabla y de ruta REST
    label: str                     # singular, para títulos
    plural: str                    # plural, para menús
    icon: str                      # emoji para el menú
    fields: list[F]
    per_obra: bool = True          # lleva columna obra_id
    title_field: str = "nombre"    # campo que se usa como etiqueta al referenciar
    order_by: str = "id DESC"
    group_order: list[str] = dc_field(default_factory=list)
    color: str = "#2563eb"

    def to_dict(self) -> dict:
        groups = self.group_order or list(dict.fromkeys(f.group for f in self.fields))
        return {
            "key": self.key, "label": self.label, "plural": self.plural,
            "icon": self.icon, "per_obra": self.per_obra,
            "title_field": self.title_field, "color": self.color,
            "groups": groups,
            "fields": [f.to_dict() for f in self.fields],
        }


# ═══════════════════════════════════════════════════════════════════════════
#  OBRAS  ·  la ficha maestra del proyecto
# ═══════════════════════════════════════════════════════════════════════════
OBRA = Entity(
    key="obras", label="Obra", plural="Obras", icon="🏗️", per_obra=False,
    title_field="nombre", order_by="COALESCE(fecha_inicio,'') DESC, id DESC",
    color="#0f766e",
    group_order=["Identificación", "Emplazamiento", "Contactos", "Planificación",
                 "Económico", "Alcance técnico", "Notas"],
    fields=[
        F("nombre", "Nombre del proyecto", req=True, list=True, group="Identificación", width=2),
        F("codigo", "Código interno / OT", list=True, group="Identificación",
          help="Ej. OT2X-12345"),
        F("cliente", "Cliente", type="select", cat="_clientes", list=True,
          group="Identificación", default="Telefónica Soluciones"),
        F("cliente_final", "Cliente final / Propiedad", group="Identificación",
          help="El dueño de la nave (Amazon, Carrefour, DHL…)"),
        F("num_pedido", "Nº Pedido / Contrato", group="Identificación"),
        F("num_oferta", "Nº Oferta", group="Identificación"),
        F("expediente", "Expediente / Referencia cliente", group="Identificación"),
        F("tipo_obra", "Tipo de obra", type="select", cat="tipo_obra", group="Identificación"),
        F("tipo_instalacion", "Tipo de instalación", type="select", cat="tipo_instalacion",
          group="Identificación", default="Nave logística"),
        F("estado", "Estado", type="select", cat="estado_obra", req=True, list=True,
          group="Identificación", default="Preparación"),

        F("direccion", "Dirección", type="textarea", group="Emplazamiento", width=2),
        F("poblacion", "Población", list=True, group="Emplazamiento"),
        F("provincia", "Provincia", group="Emplazamiento"),
        F("cp", "Código postal", group="Emplazamiento"),
        F("coordenadas", "Coordenadas GPS", group="Emplazamiento",
          help="lat,lon — se abre en Google Maps desde la ficha"),
        F("superficie_m2", "Superficie (m²)", type="number", group="Emplazamiento"),
        F("num_naves", "Nº de naves / módulos", type="int", group="Emplazamiento"),
        F("horario_acceso", "Horario de acceso a obra", group="Emplazamiento",
          help="Ej. L-V 07:00-19:00. Sábados con permiso."),
        F("requisitos_acceso", "Requisitos de acceso", type="textarea", group="Emplazamiento",
          width=2, help="PRL, CAE, badge, formación específica, EPIs obligatorios…"),

        F("jefe_obra", "Jefe de obra", list=True, group="Contactos"),
        F("telefono_jefe", "Teléfono jefe de obra", type="tel", group="Contactos"),
        F("email_jefe", "Email jefe de obra", type="email", group="Contactos"),
        F("interlocutor_cliente", "Interlocutor del cliente", group="Contactos"),
        F("telefono_cliente", "Teléfono del interlocutor", type="tel", group="Contactos"),
        F("email_cliente", "Email del interlocutor", type="email", group="Contactos"),
        F("delegacion", "Delegación / Zona", group="Contactos"),
        F("cra", "CRA (Central Receptora)", group="Contactos",
          help="Central receptora de alarmas a la que se conecta la instalación"),
        F("cra_contacto", "Contacto CRA", group="Contactos"),

        F("fecha_inicio", "Fecha de inicio", type="date", list=True, group="Planificación"),
        F("fecha_fin_prevista", "Fecha fin prevista", type="date", list=True, group="Planificación"),
        F("fecha_fin_real", "Fecha fin real", type="date", group="Planificación"),
        F("fecha_recepcion", "Fecha de recepción", type="date", group="Planificación"),
        F("plazo_dias", "Plazo contractual (días)", type="int", group="Planificación"),
        F("penalizacion_dia", "Penalización por día (€)", type="money", group="Planificación"),
        F("garantia_meses", "Garantía (meses)", type="int", group="Planificación", default=24),

        F("importe_contrato", "Importe del contrato (€)", type="money", list=True, group="Económico"),
        F("importe_ampliaciones", "Ampliaciones aprobadas (€)", type="money", group="Económico",
          help="Se calcula solo desde Ofertas aprobadas, pero puedes forzarlo"),
        F("retencion_pct", "Retención (%)", type="percent", group="Económico"),
        F("forma_pago", "Forma de pago", group="Económico"),
        F("certificacion_periodicidad", "Periodicidad certificación", type="select",
          options=["Mensual", "Por hitos", "A fin de obra", "Otra"], group="Económico"),

        F("alcance", "Alcance de los trabajos", type="textarea", group="Alcance técnico", width=2),
        F("num_camaras", "Nº de cámaras", type="int", group="Alcance técnico"),
        F("num_lectores", "Nº de lectores de acceso", type="int", group="Alcance técnico"),
        F("num_detectores", "Nº de detectores intrusión", type="int", group="Alcance técnico"),
        F("marca_cctv", "Marca CCTV", group="Alcance técnico"),
        F("marca_intrusion", "Marca intrusión", group="Alcance técnico"),
        F("marca_accesos", "Marca control de accesos", group="Alcance técnico"),
        F("vms", "VMS / Software", group="Alcance técnico"),
        F("rango_ip", "Rango IP de la instalación", group="Alcance técnico",
          help="Ej. 10.20.30.0/24 — se usa para validar IPs duplicadas"),
        F("vlan", "VLAN", group="Alcance técnico"),

        F("carpeta", "Carpeta de obra en disco", group="Notas", width=2,
          help="Ruta local donde se crea la estructura de carpetas"),
        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  TAREAS  ·  planificación y avance (alimenta el Gantt)
# ═══════════════════════════════════════════════════════════════════════════
TAREA = Entity(
    key="tareas", label="Tarea", plural="Tareas", icon="✅", title_field="tarea",
    order_by="COALESCE(fecha_inicio,'9999') ASC, id ASC", color="#2563eb",
    group_order=["Definición", "Planificación", "Recursos", "Económico", "Notas"],
    fields=[
        F("tarea", "Tarea", req=True, list=True, group="Definición", width=2),
        F("categoria", "Categoría", type="select", cat="categoria_tarea", list=True,
          group="Definición"),
        F("zona", "Zona / Ubicación", type="select", cat="_zonas", group="Definición"),
        F("prioridad", "Prioridad", type="select", cat="prioridad", list=True,
          group="Definición", default="Media"),
        F("estado", "Estado", type="select", cat="estado_tarea", req=True, list=True,
          group="Definición", default="No iniciada"),
        F("avance", "% Avance", type="percent", list=True, group="Definición", default=0),
        F("descripcion", "Descripción", type="textarea", group="Definición", width=2),

        F("fecha_inicio", "Inicio", type="date", list=True, group="Planificación"),
        F("fecha_fin", "Fin previsto", type="date", list=True, group="Planificación"),
        F("fecha_fin_real", "Fin real", type="date", group="Planificación"),
        F("duracion_h", "Duración estimada (h)", type="number", group="Planificación"),
        F("depende_de", "Depende de la tarea", type="ref", ref="tareas", group="Planificación",
          help="La tarea no puede empezar hasta que ésta termine"),
        F("hito", "Es un hito de facturación", type="bool", group="Planificación"),

        F("subcontrata_id", "Subcontrata responsable", type="ref", ref="subcontratas",
          list=True, group="Recursos"),
        F("responsable", "Responsable", group="Recursos"),
        F("equipo", "Equipo asignado", group="Recursos", help="Nombres separados por coma"),
        F("num_operarios", "Nº de operarios", type="int", group="Recursos"),

        F("coste_previsto", "Coste previsto (€)", type="money", group="Económico"),
        F("coste_mo", "Coste mano de obra (€)", type="money", group="Económico"),
        F("certificable", "Importe certificable (€)", type="money", group="Económico"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  DISPOSITIVOS  ·  INVENTARIO DE INSTALACIÓN (no de obra)
#  Es el módulo estrella: lo que la IA rellena desde la foto de la etiqueta.
# ═══════════════════════════════════════════════════════════════════════════
DISPOSITIVO = Entity(
    key="dispositivos", label="Dispositivo", plural="Inventario instalación",
    icon="📹", title_field="etiqueta", order_by="etiqueta ASC, id ASC", color="#7c3aed",
    group_order=["Identificación", "Ubicación", "Red", "Instalación",
                 "Configuración", "Pruebas", "Garantía", "Notas"],
    fields=[
        F("etiqueta", "Etiqueta / Nombre", req=True, list=True, group="Identificación",
          help="Como aparece en el VMS y en el rotulado físico. Ej. CAM-MUELLE-01"),
        F("categoria", "Categoría", type="select", cat="categoria_dispositivo", list=True,
          req=True, group="Identificación"),
        F("tipo", "Tipo de dispositivo", type="select", cat="tipo_dispositivo", list=True,
          group="Identificación"),
        F("marca", "Marca", list=True, group="Identificación"),
        F("modelo", "Modelo", list=True, group="Identificación"),
        F("num_serie", "Nº de serie", list=True, group="Identificación",
          help="Se extrae automáticamente de la foto de la etiqueta"),
        F("part_number", "Part number / Referencia", group="Identificación"),
        F("cantidad", "Cantidad", type="int", group="Identificación", default=1),
        F("estado", "Estado", type="select", cat="estado_dispositivo", req=True, list=True,
          group="Identificación", default="Previsto"),

        F("zona", "Zona", type="select", cat="_zonas", list=True, group="Ubicación"),
        F("ubicacion", "Ubicación exacta", group="Ubicación", width=2,
          help="Ej. Muelle 4, sobre puerta seccional, orientada a playa de camiones"),
        F("planta", "Planta / Nivel", group="Ubicación"),
        F("altura_m", "Altura de montaje (m)", type="number", group="Ubicación"),
        F("tipo_montaje", "Tipo de montaje", type="select", cat="tipo_montaje", group="Ubicación"),
        F("orientacion", "Orientación / Campo de visión", group="Ubicación"),
        F("plano_ref", "Referencia en plano", group="Ubicación"),
        F("coordenadas", "Coordenadas GPS", group="Ubicación"),

        F("ip", "Dirección IP", type="ip", list=True, group="Red",
          help="Se avisa automáticamente si la IP está duplicada en la obra"),
        F("mascara", "Máscara de red", group="Red", default="255.255.255.0"),
        F("gateway", "Puerta de enlace", type="ip", group="Red"),
        F("mac", "Dirección MAC", type="mac", list=True, group="Red"),
        F("vlan", "VLAN", group="Red"),
        F("switch_id", "Switch / Rack", group="Red"),
        F("puerto_switch", "Puerto del switch", group="Red"),
        F("poe", "Alimentación PoE", type="select",
          options=["No", "PoE (802.3af)", "PoE+ (802.3at)", "PoE++ (802.3bt)", "12V DC", "24V AC", "230V AC"],
          group="Red"),
        F("consumo_w", "Consumo (W)", type="number", group="Red"),
        F("grabador", "Grabador / Central asociada", group="Red",
          help="NVR, DVR o central de intrusión a la que reporta"),
        F("canal", "Canal / Zona en grabador", group="Red"),

        F("fecha_instalacion", "Fecha de instalación", type="date", group="Instalación"),
        F("tecnico", "Técnico instalador", group="Instalación"),
        F("subcontrata_id", "Subcontrata", type="ref", ref="subcontratas", group="Instalación"),
        F("cable_tipo", "Tipo de cable", group="Instalación",
          help="Ej. UTP CAT6, manguera 4+2, fibra OM3"),
        F("cable_metros", "Metros de cable", type="number", group="Instalación"),
        F("desde_rack", "Desde (rack/registro)", group="Instalación"),

        F("firmware", "Versión de firmware", group="Configuración"),
        F("usuario", "Usuario de acceso", group="Configuración"),
        F("password_ref", "Referencia de contraseña", group="Configuración",
          help="NO guardes la contraseña: pon aquí dónde está (gestor, sobre, ficha CRA)"),
        F("resolucion", "Resolución / Capacidad", group="Configuración"),
        F("fps", "FPS", type="int", group="Configuración"),
        F("dias_grabacion", "Días de grabación", type="int", group="Configuración"),
        F("configurado_vms", "Dado de alta en VMS", type="bool", group="Configuración"),
        F("configurado_cra", "Dado de alta en CRA", type="bool", group="Configuración"),

        F("prueba_visual", "Prueba de imagen/función", type="select", cat="resultado_prueba",
          group="Pruebas", default="Pendiente"),
        F("prueba_nocturna", "Prueba nocturna / IR", type="select", cat="resultado_prueba",
          group="Pruebas", default="Pendiente"),
        F("prueba_grabacion", "Prueba de grabación", type="select", cat="resultado_prueba",
          group="Pruebas", default="Pendiente"),
        F("prueba_cra", "Prueba señal a CRA", type="select", cat="resultado_prueba",
          group="Pruebas", default="Pendiente"),
        F("fecha_prueba", "Fecha de pruebas", type="date", group="Pruebas"),
        F("observaciones_prueba", "Observaciones de pruebas", type="textarea",
          group="Pruebas", width=2),

        F("proveedor", "Proveedor", group="Garantía"),
        F("albaran", "Albarán / Pedido", group="Garantía"),
        F("fecha_compra", "Fecha de compra", type="date", group="Garantía"),
        F("garantia_hasta", "Garantía hasta", type="date", group="Garantía"),
        F("precio", "Precio unitario (€)", type="money", group="Garantía"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  MATERIALES  ·  almacén de obra
# ═══════════════════════════════════════════════════════════════════════════
MATERIAL = Entity(
    key="materiales", label="Material", plural="Materiales", icon="📦",
    title_field="material", order_by="material ASC", color="#b45309",
    group_order=["Material", "Stock", "Compra", "Notas"],
    fields=[
        F("material", "Material", req=True, list=True, group="Material", width=2),
        F("codigo", "Código / Referencia", list=True, group="Material"),
        F("categoria", "Categoría", type="select", cat="categoria_material", list=True,
          group="Material"),
        F("unidad", "Unidad", type="select", cat="unidad", group="Material", default="ud"),
        F("marca", "Marca", group="Material"),

        F("recibido", "Cantidad recibida", type="number", list=True, group="Stock", default=0),
        F("stock_min", "Stock mínimo", type="number", group="Stock",
          help="Por debajo de este valor salta la alerta de reposición"),
        F("ubicacion_almacen", "Ubicación en almacén", group="Stock"),

        F("proveedor", "Proveedor", list=True, group="Compra"),
        F("precio", "Precio unitario (€)", type="money", list=True, group="Compra"),
        F("fecha_recepcion", "Fecha última recepción", type="date", group="Compra"),
        F("albaran", "Albarán", group="Compra"),
        F("pedido", "Nº de pedido", group="Compra"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

CONSUMO = Entity(
    key="consumos", label="Consumo", plural="Consumos", icon="📉",
    title_field="material", order_by="fecha DESC, id DESC", color="#a16207",
    group_order=["Consumo", "Notas"],
    fields=[
        F("fecha", "Fecha", type="date", req=True, list=True, group="Consumo"),
        F("material_id", "Material", type="ref", ref="materiales", req=True, list=True,
          group="Consumo"),
        F("cantidad", "Cantidad", type="number", req=True, list=True, group="Consumo"),
        F("tarea_id", "Tarea", type="ref", ref="tareas", list=True, group="Consumo"),
        F("zona", "Zona", type="select", cat="_zonas", group="Consumo"),
        F("registrado_por", "Registrado por", list=True, group="Consumo"),
        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  SUBCONTRATAS  ·  control económico y documental
# ═══════════════════════════════════════════════════════════════════════════
SUBCONTRATA = Entity(
    key="subcontratas", label="Subcontrata", plural="Subcontratas", icon="🤝",
    title_field="nombre", order_by="nombre ASC", color="#c026d3",
    group_order=["Empresa", "Contacto", "Económico", "Documentación", "Notas"],
    fields=[
        F("nombre", "Subcontrata", req=True, list=True, group="Empresa", width=2),
        F("cif", "CIF / NIF", list=True, group="Empresa"),
        F("especialidad", "Especialidad", type="select", cat="especialidad_subcontrata",
          list=True, group="Empresa"),
        F("estado", "Estado", type="select", cat="estado_subcontrata", list=True,
          group="Empresa", default="Pendiente contrato"),
        F("valoracion", "Valoración (1-5)", type="int", group="Empresa",
          help="Tu nota interna para futuras obras"),

        F("contacto", "Persona de contacto", list=True, group="Contacto"),
        F("telefono", "Teléfono", type="tel", list=True, group="Contacto"),
        F("email", "Email", type="email", group="Contacto"),
        F("direccion", "Dirección", type="textarea", group="Contacto", width=2),

        F("importe_contratado", "Importe contratado (€)", type="money", list=True, group="Económico"),
        F("importe_certificado", "Importe certificado (€)", type="money", group="Económico"),
        F("importe_pagado", "Importe pagado (€)", type="money", group="Económico"),
        F("fecha_inicio", "Fecha inicio", type="date", group="Económico"),
        F("fecha_fin", "Fecha fin prevista", type="date", group="Económico"),

        F("contrato_firmado", "Contrato firmado", type="bool", group="Documentación"),
        F("seguro_rc", "Seguro RC vigente", type="select", cat="si_no_np", list=True,
          group="Documentación"),
        F("seguro_rc_vence", "Vencimiento seguro RC", type="date", group="Documentación"),
        F("prl_ok", "PRL / CAE entregada", type="select", cat="si_no_np", group="Documentación"),
        F("cae_plataforma", "Plataforma CAE", group="Documentación",
          help="Ej. e-coordina, CTAIMA, Dokify…"),
        F("rea", "Nº REA", group="Documentación",
          help="Registro de Empresas Acreditadas — obligatorio en construcción"),
        F("itss_al_corriente", "Al corriente Seg. Social", type="select", cat="si_no_np",
          group="Documentación"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  PERSONAL  ·  control de accesos y PRL
# ═══════════════════════════════════════════════════════════════════════════
PERSONAL = Entity(
    key="personal", label="Persona", plural="Personal", icon="👷",
    title_field="nombre", order_by="nombre ASC", color="#0891b2",
    group_order=["Persona", "Acceso y PRL", "Coste", "Notas"],
    fields=[
        F("nombre", "Nombre y apellidos", req=True, list=True, group="Persona", width=2),
        F("dni", "DNI / NIE", list=True, group="Persona"),
        F("empresa", "Empresa", list=True, group="Persona"),
        F("subcontrata_id", "Subcontrata", type="ref", ref="subcontratas", group="Persona"),
        F("oficio", "Oficio / Categoría", type="select", cat="oficio", list=True, group="Persona"),
        F("telefono", "Teléfono", type="tel", group="Persona"),
        F("email", "Email", type="email", group="Persona"),

        F("estado", "Estado de acceso", type="select", cat="estado_personal", req=True,
          list=True, group="Acceso y PRL", default="VALIDANDO"),
        F("fecha_alta", "Fecha de alta en obra", type="date", group="Acceso y PRL"),
        F("fecha_baja", "Fecha de baja", type="date", group="Acceso y PRL"),
        F("formacion_prl", "Formación PRL", type="select", cat="si_no_np", group="Acceso y PRL"),
        F("prl_horas", "Horas de formación PRL", type="int", group="Acceso y PRL"),
        F("reconocimiento_medico", "Reconocimiento médico", type="select", cat="si_no_np",
          group="Acceso y PRL"),
        F("medico_vence", "Vence reconocimiento", type="date", group="Acceso y PRL"),
        F("tpc", "TPC / Tarjeta profesional", type="select", cat="si_no_np", group="Acceso y PRL"),
        F("badge", "Nº de acreditación / Badge", group="Acceso y PRL"),
        F("autorizado_pemp", "Autorizado PEMP", type="bool", group="Acceso y PRL"),
        F("autorizado_altura", "Autorizado trabajos en altura", type="bool", group="Acceso y PRL"),

        F("horas", "Horas totales", type="number", list=True, group="Coste"),
        F("precio_hora", "Precio hora (€)", type="money", group="Coste"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  MAQUINARIA  ·  medios auxiliares
# ═══════════════════════════════════════════════════════════════════════════
MAQUINARIA = Entity(
    key="maquinaria", label="Equipo", plural="Maquinaria", icon="🏗",
    title_field="equipo", order_by="equipo ASC", color="#ca8a04",
    group_order=["Equipo", "Periodo", "Documentación", "Notas"],
    fields=[
        F("equipo", "Equipo / Máquina", req=True, list=True, group="Equipo", width=2),
        F("tipo", "Tipo", type="select", cat="tipo_maquinaria", list=True, group="Equipo"),
        F("propiedad", "Propiedad", type="select", cat="propiedad_maquinaria", group="Equipo"),
        F("proveedor", "Proveedor", list=True, group="Equipo"),
        F("matricula", "Matrícula / Nº serie", group="Equipo"),
        F("altura_trabajo", "Altura de trabajo (m)", type="number", group="Equipo"),
        F("estado", "Estado", type="select", cat="estado_maquinaria", list=True,
          group="Equipo", default="Solicitada"),
        F("operario", "Operario asignado", group="Equipo"),

        F("fecha_entrada", "Entrada en obra", type="date", list=True, group="Periodo"),
        F("fecha_salida", "Salida de obra", type="date", group="Periodo"),
        F("coste_dia", "Coste por día (€)", type="money", group="Periodo"),
        F("coste_transporte", "Coste transporte (€)", type="money", group="Periodo"),

        F("proxima_itv", "Próxima ITV / Revisión", type="date", list=True, group="Documentación",
          help="Salta alerta a 30 días vista"),
        F("seguro_vence", "Vencimiento seguro", type="date", group="Documentación"),
        F("certificado_ok", "Certificado / Marcado CE", type="select", cat="si_no_np",
          group="Documentación"),
        F("manual_entregado", "Manual entregado", type="bool", group="Documentación"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  INCIDENCIAS
# ═══════════════════════════════════════════════════════════════════════════
INCIDENCIA = Entity(
    key="incidencias", label="Incidencia", plural="Incidencias", icon="⚠️",
    title_field="titulo", order_by="id DESC", color="#dc2626",
    group_order=["Incidencia", "Gestión", "Impacto", "Notas"],
    fields=[
        F("titulo", "Título", req=True, list=True, group="Incidencia", width=2),
        F("fecha", "Fecha", type="date", req=True, list=True, group="Incidencia"),
        F("tipo", "Tipo", type="select", cat="tipo_incidencia", list=True, group="Incidencia"),
        F("gravedad", "Gravedad", type="select", cat="gravedad", req=True, list=True,
          group="Incidencia", default="Leve"),
        F("zona", "Zona / Ubicación", type="select", cat="_zonas", group="Incidencia"),
        F("descripcion", "Descripción", type="textarea", group="Incidencia", width=2),
        F("detectada_por", "Detectada por", group="Incidencia"),

        F("estado", "Estado", type="select", cat="estado_incidencia", req=True, list=True,
          group="Gestión", default="Abierta"),
        F("responsable", "Responsable de resolver", list=True, group="Gestión"),
        F("subcontrata_id", "Subcontrata implicada", type="ref", ref="subcontratas", group="Gestión"),
        F("fecha_limite", "Fecha límite", type="date", list=True, group="Gestión"),
        F("fecha_cierre", "Fecha de cierre", type="date", group="Gestión"),
        F("accion_correctiva", "Acción correctiva", type="textarea", group="Gestión", width=2),
        F("accion_preventiva", "Acción preventiva", type="textarea", group="Gestión", width=2),

        F("coste", "Coste asociado (€)", type="money", group="Impacto"),
        F("retraso_dias", "Retraso generado (días)", type="int", group="Impacto"),
        F("afecta_plazo", "Afecta al plazo de obra", type="bool", group="Impacto"),
        F("reclamable", "Reclamable al cliente", type="bool", group="Impacto"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  DOCUMENTOS / PLANOS
# ═══════════════════════════════════════════════════════════════════════════
DOCUMENTO = Entity(
    key="documentos", label="Documento", plural="Documentos", icon="📄",
    title_field="documento", order_by="id DESC", color="#475569",
    group_order=["Documento", "Seguimiento", "Notas"],
    fields=[
        F("documento", "Documento", req=True, list=True, group="Documento", width=2),
        F("categoria", "Categoría", type="select", cat="categoria_documento", list=True,
          group="Documento"),
        F("version", "Versión", group="Documento"),
        F("enlace", "Archivo / Enlace", type="url", group="Documento", width=2),

        F("estado", "Estado", type="select", cat="estado_documento", req=True, list=True,
          group="Seguimiento", default="Pendiente"),
        F("responsable", "Responsable", list=True, group="Seguimiento"),
        F("fecha_limite", "Fecha límite", type="date", list=True, group="Seguimiento"),
        F("fecha_entrega", "Entregado el", type="date", group="Seguimiento"),
        F("obligatorio", "Obligatorio para cierre", type="bool", group="Seguimiento"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

PLANO = Entity(
    key="planos", label="Plano", plural="Planos", icon="📐",
    title_field="nombre", order_by="codigo ASC", color="#334155",
    group_order=["Plano", "Revisión", "Notas"],
    fields=[
        F("codigo", "Código", list=True, group="Plano"),
        F("nombre", "Nombre del plano", req=True, list=True, group="Plano", width=2),
        F("disciplina", "Disciplina", type="select", cat="disciplina_plano", list=True,
          group="Plano"),
        F("escala", "Escala", group="Plano"),
        F("enlace", "Archivo / Enlace", type="url", group="Plano", width=2),

        F("revision", "Revisión actual", list=True, group="Revisión"),
        F("fecha_revision", "Fecha de revisión", type="date", list=True, group="Revisión"),
        F("motivo_cambio", "Motivo del cambio", type="textarea", group="Revisión", width=2),
        F("estado", "Estado", type="select", cat="estado_plano", list=True, group="Revisión",
          default="Solicitado"),
        F("responsable", "Responsable", group="Revisión"),
        F("aprobado_por", "Aprobado por", group="Revisión"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  VISITAS  ·  fichas de visita de obra
# ═══════════════════════════════════════════════════════════════════════════
VISITA = Entity(
    key="visitas", label="Visita", plural="Visitas", icon="📋",
    title_field="motivo", order_by="fecha DESC, id DESC", color="#059669",
    group_order=["Visita", "Contenido", "Notas"],
    fields=[
        F("fecha", "Fecha", type="date", req=True, list=True, group="Visita"),
        F("hora", "Hora", group="Visita"),
        F("tipo", "Tipo de visita", type="select", cat="tipo_visita", list=True, group="Visita"),
        F("motivo", "Motivo principal", req=True, list=True, group="Visita", width=2),
        F("asistentes", "Asistentes", type="textarea", group="Visita", width=2),
        F("interlocutor", "Persona visitada", list=True, group="Visita"),

        F("temas_tratados", "Temas tratados", type="textarea", group="Contenido", width=2),
        F("acuerdos", "Acuerdos alcanzados", type="textarea", group="Contenido", width=2),
        F("pendientes", "Pendientes / Próximos pasos", type="textarea", group="Contenido", width=2),
        F("avance_observado", "Avance observado (%)", type="percent", group="Contenido"),
        F("proxima_visita", "Próxima visita", type="date", group="Contenido"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  PARTES DIARIOS
# ═══════════════════════════════════════════════════════════════════════════
PARTE = Entity(
    key="partes", label="Parte diario", plural="Partes diarios", icon="🗓️",
    title_field="fecha", order_by="fecha DESC, id DESC", color="#4f46e5",
    group_order=["Jornada", "Trabajos", "Notas"],
    fields=[
        F("fecha", "Fecha", type="date", req=True, list=True, group="Jornada"),
        F("meteorologia", "Meteorología", type="select", cat="meteorologia", group="Jornada"),
        F("hora_entrada", "Hora entrada", group="Jornada"),
        F("hora_salida", "Hora salida", group="Jornada"),
        F("personal_presente", "Personal en obra", type="int", list=True, group="Jornada"),
        F("horas_totales", "Horas totales", type="number", list=True, group="Jornada"),
        F("subcontratas_presentes", "Subcontratas presentes", group="Jornada", width=2),

        F("trabajos", "Trabajos realizados", type="textarea", req=True, list=True,
          group="Trabajos", width=2),
        F("zonas", "Zonas intervenidas", group="Trabajos", width=2),
        F("material_recibido", "Material recibido", type="textarea", group="Trabajos", width=2),
        F("incidencias_jornada", "Incidencias de la jornada", type="textarea",
          group="Trabajos", width=2),
        F("visitas_recibidas", "Visitas recibidas", group="Trabajos", width=2),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  OFERTAS / AMPLIACIONES
# ═══════════════════════════════════════════════════════════════════════════
OFERTA = Entity(
    key="ofertas", label="Ampliación", plural="Ofertas y ampliaciones", icon="💰",
    title_field="descripcion", order_by="id DESC", color="#16a34a",
    group_order=["Ampliación", "Económico", "Seguimiento", "Notas"],
    fields=[
        F("codigo", "Código", list=True, group="Ampliación"),
        F("descripcion", "Descripción", req=True, list=True, group="Ampliación", width=2),
        F("motivo", "Motivo", type="select", cat="motivo_ampliacion", list=True,
          group="Ampliación"),
        F("categoria", "Categoría de coste", type="select", cat="categoria_coste",
          group="Ampliación"),
        F("solicitante", "Solicitado por", group="Ampliación"),

        F("importe", "Importe ofertado (€)", type="money", req=True, list=True, group="Económico"),
        F("coste", "Coste estimado (€)", type="money", group="Económico"),
        F("margen_pct", "Margen (%)", type="percent", group="Económico"),
        F("plazo_adicional", "Plazo adicional (días)", type="int", group="Económico"),

        F("estado", "Estado", type="select", cat="estado_oferta", req=True, list=True,
          group="Seguimiento", default="Borrador"),
        F("fecha_envio", "Fecha de envío", type="date", list=True, group="Seguimiento"),
        F("fecha_respuesta", "Fecha de respuesta", type="date", group="Seguimiento"),
        F("aprobada_por", "Aprobada por", group="Seguimiento"),
        F("documento", "Documento / Enlace", type="url", group="Seguimiento", width=2),
        F("facturada", "Facturada", type="bool", group="Seguimiento"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  CERTIFICACIONES  ·  facturación por hitos
# ═══════════════════════════════════════════════════════════════════════════
CERTIFICACION = Entity(
    key="certificaciones", label="Certificación", plural="Certificaciones", icon="🧾",
    title_field="concepto", order_by="fecha DESC, id DESC", color="#15803d",
    group_order=["Certificación", "Cobro", "Notas"],
    fields=[
        F("numero", "Nº certificación", list=True, group="Certificación"),
        F("concepto", "Concepto", req=True, list=True, group="Certificación", width=2),
        F("fecha", "Fecha", type="date", req=True, list=True, group="Certificación"),
        F("periodo", "Periodo", group="Certificación"),
        F("importe", "Importe (€)", type="money", req=True, list=True, group="Certificación"),
        F("porcentaje_obra", "% de obra certificado", type="percent", group="Certificación"),
        F("retencion", "Retención aplicada (€)", type="money", group="Certificación"),

        F("estado", "Estado", type="select",
          options=["Pendiente aprobación", "Aprobada", "Facturada", "Cobrada", "Rechazada"],
          req=True, list=True, group="Cobro", default="Pendiente aprobación"),
        F("num_factura", "Nº de factura", group="Cobro"),
        F("fecha_factura", "Fecha de factura", type="date", group="Cobro"),
        F("fecha_cobro_prevista", "Cobro previsto", type="date", list=True, group="Cobro"),
        F("fecha_cobro", "Fecha de cobro", type="date", group="Cobro"),

        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  PRESUPUESTO  ·  partidas previsto vs real
# ═══════════════════════════════════════════════════════════════════════════
PARTIDA = Entity(
    key="partidas", label="Partida", plural="Presupuesto", icon="📊",
    title_field="concepto", order_by="id ASC", color="#0d9488",
    group_order=["Partida", "Notas"],
    fields=[
        F("concepto", "Concepto", req=True, list=True, group="Partida", width=2),
        F("categoria", "Categoría de coste", type="select", cat="categoria_coste", req=True,
          list=True, group="Partida"),
        F("presupuestado", "Presupuestado (€)", type="money", list=True, group="Partida"),
        F("comprometido", "Comprometido (€)", type="money", group="Partida",
          help="Pedidos y contratos firmados aunque no facturados"),
        F("real", "Coste real (€)", type="money", list=True, group="Partida"),
        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
#  CONTACTOS  ·  agenda (global, no por obra)
# ═══════════════════════════════════════════════════════════════════════════
CONTACTO = Entity(
    key="contactos", label="Contacto", plural="Agenda", icon="📇", per_obra=False,
    title_field="nombre", order_by="nombre ASC", color="#7c3aed",
    group_order=["Contacto", "Notas"],
    fields=[
        F("nombre", "Nombre", req=True, list=True, group="Contacto", width=2),
        F("empresa", "Empresa", list=True, group="Contacto"),
        F("tipo", "Tipo", type="select", cat="tipo_contacto", list=True, group="Contacto"),
        F("cargo", "Cargo", group="Contacto"),
        F("telefono", "Teléfono", type="tel", list=True, group="Contacto"),
        F("telefono2", "Teléfono 2", type="tel", group="Contacto"),
        F("email", "Email", type="email", list=True, group="Contacto"),
        F("zona", "Zona / Delegación", group="Contacto"),
        F("notas", "Notas", type="textarea", group="Notas", width=2),
    ],
)

# ═══════════════════════════════════════════════════════════════════════════
ENTITIES: dict[str, Entity] = {
    e.key: e for e in [
        OBRA, TAREA, DISPOSITIVO, MATERIAL, CONSUMO, SUBCONTRATA, PERSONAL,
        MAQUINARIA, INCIDENCIA, DOCUMENTO, PLANO, VISITA, PARTE, OFERTA,
        CERTIFICACION, PARTIDA, CONTACTO,
    ]
}

# Orden del menú lateral.
MENU = [
    "tareas", "dispositivos", "materiales", "consumos", "partes", "incidencias",
    "subcontratas", "personal", "maquinaria", "visitas", "documentos", "planos",
    "ofertas", "certificaciones", "partidas", "contactos",
]


def entity(key: str) -> Entity:
    if key not in ENTITIES:
        raise KeyError(f"Entidad desconocida: {key}")
    return ENTITIES[key]
