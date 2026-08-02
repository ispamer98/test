"""
Catálogos del dominio: instalaciones de seguridad en naves logísticas.

Todas las listas desplegables de la aplicación viven aquí. El usuario puede
ampliarlas desde Ajustes (se guardan en la tabla `catalogo_extra` y se fusionan
con estas por defecto), pero nunca se pierde la base.

Origen: hojas "Listas" de los libros Excel del usuario + práctica habitual de
obra en subcontratación para operadora (Telefónica) en naves logísticas.
"""

CATALOGOS: dict[str, list[str]] = {
    # ------------------------------------------------------------------ obra
    "estado_obra": [
        "Preparación", "Replanteo", "En curso", "Pausada",
        "Pendiente cliente", "En pruebas", "Finalizada", "Garantía", "Cancelada",
    ],
    "tipo_obra": [
        "Obra nueva", "Ampliación", "Reforma", "Sustitución tecnológica",
        "Mantenimiento correctivo", "Traslado", "Desmontaje",
    ],
    "tipo_instalacion": [
        "Nave logística", "Centro de distribución", "Nave industrial",
        "Oficinas", "Retail / Tienda", "Aparcamiento", "Perímetro exterior",
        "Centro de datos", "Otros",
    ],
    # --------------------------------------------------------------- tareas
    "categoria_tarea": [
        "Replanteo", "Obra Civil", "Canalización", "Cableado", "CCTV",
        "Intrusión", "Control de Accesos", "Megafonía/PA", "Contraincendios",
        "Redes y Datos", "Electricidad", "Domótica/BMS", "Configuración",
        "Pruebas y Puesta en Marcha", "Formación", "Documentación", "Otros",
    ],
    "estado_tarea": [
        "No iniciada", "En curso", "Bloqueada", "En revisión",
        "Completada", "Cancelada",
    ],
    "prioridad": ["Baja", "Media", "Alta", "Crítica"],
    # ---------------------------------------------------------- dispositivos
    "categoria_dispositivo": [
        "CCTV", "Intrusión", "Control de Accesos", "Megafonía/PA",
        "Detección de Incendios", "Redes y Cableado", "Alimentación/SAI",
        "Interfonía", "Domótica/BMS", "Otros",
    ],
    "tipo_dispositivo": [
        # CCTV
        "Cámara IP Bullet", "Cámara IP Domo", "Cámara IP PTZ",
        "Cámara IP Fisheye", "Cámara IP Multisensor", "Cámara Térmica",
        "Cámara ANPR/LPR", "NVR", "DVR", "Servidor de vídeo", "Monitor",
        "Videowall", "Licencia VMS",
        # Intrusión
        "Central de Intrusión", "Teclado", "Detector Volumétrico PIR",
        "Detector Doble Tecnología", "Detector Sísmico", "Contacto Magnético",
        "Barrera Infrarroja", "Detector Exterior", "Sirena Interior",
        "Sirena Exterior", "Comunicador CRA", "Módulo Expansor", "Fuente/Batería",
        # Accesos
        "Controladora de Accesos", "Lector Proximidad", "Lector Biométrico",
        "Lector Teclado", "Cerradura Electromagnética", "Cerradero Eléctrico",
        "Pulsador de Salida", "Botón de Emergencia", "Torno", "Barrera Vehicular",
        "Molinete", "Videoportero", "Placa de Calle",
        # Redes / soporte
        "Switch PoE", "Switch", "Router", "Firewall", "Rack", "Patch Panel",
        "SAI/UPS", "Inyector PoE", "Convertidor de Medios", "Antena/Radioenlace",
        # Otros
        "Megafonía - Amplificador", "Megafonía - Altavoz", "Central de Incendios",
        "Detector de Humo", "Pulsador de Alarma", "Otros",
    ],
    "estado_dispositivo": [
        "Previsto", "Pedido", "En almacén", "Recibido en obra", "Instalado",
        "Conexionado", "Configurado", "Probado", "Entregado",
        "Averiado", "Devuelto", "Pendiente sustitución",
    ],
    "resultado_prueba": ["Pendiente", "OK", "OK con observaciones", "KO", "No aplica"],
    "tipo_montaje": [
        "Pared", "Techo", "Falso techo", "Poste", "Báculo", "Estructura/Celosía",
        "Rack", "Empotrado", "Superficie", "Otros",
    ],
    # ---------------------------------------------------------- materiales
    "categoria_material": [
        "Cableado", "Fibra Óptica", "Canalización", "Conectores/Rack", "CCTV",
        "Intrusión", "Control de Accesos", "Redes", "Electricidad",
        "Ferretería", "Soportería", "Señalización", "EPIs", "Otros",
    ],
    "unidad": ["ud", "m", "ml", "m²", "kg", "rollo", "caja", "par", "juego", "h"],
    # --------------------------------------------------------- subcontratas
    "especialidad_subcontrata": [
        "Cableado Estructurado", "CCTV", "Intrusión", "Control de Accesos",
        "Electricidad", "Obra Civil", "Andamios/PEMP", "Redes",
        "Contraincendios", "Cerrajería", "Limpieza", "Otros",
    ],
    "estado_subcontrata": [
        "Pendiente contrato", "Contratada", "Activa", "Finalizada",
        "Suspendida", "Vetada",
    ],
    # ------------------------------------------------------------- personal
    "estado_personal": ["VALIDANDO", "ACCESS", "NO ACCESS", "BAJA", "CADUCADO"],
    "oficio": [
        "Jefe de Obra", "Encargado", "Técnico de Seguridad", "Técnico de Redes",
        "Instalador", "Ayudante", "Electricista", "Oficial 1ª", "Oficial 2ª",
        "Peón", "Ingeniero", "Administrativo", "Coordinador PRL", "Otros",
    ],
    # ----------------------------------------------------------- maquinaria
    "tipo_maquinaria": [
        "PEMP Tijera", "PEMP Articulada", "PEMP Telescópica", "Andamio",
        "Andamio Rodante", "Escalera", "Grúa", "Carretilla Elevadora",
        "Elevador de Materiales", "Generador", "Furgoneta", "Otros",
    ],
    "propiedad_maquinaria": ["Propia", "Alquilada", "Subcontratada", "Del cliente"],
    "estado_maquinaria": [
        "Solicitada", "En obra", "En uso", "Parada", "En revisión/ITV",
        "Averiada", "Devuelta",
    ],
    # ---------------------------------------------------------- incidencias
    "tipo_incidencia": [
        "Calidad", "Seguridad/PRL", "Suministro", "Técnica", "Coordinación",
        "Cliente", "Subcontrata", "Acceso a obra", "Documental",
        "Daños a terceros", "Robo/Vandalismo", "Meteorología", "Otros",
    ],
    "gravedad": ["Leve", "Moderada", "Grave", "Crítica"],
    "estado_incidencia": ["Abierta", "En gestión", "Escalada", "Resuelta", "Cerrada"],
    # ---------------------------------------------------------- documentos
    "categoria_documento": [
        "Oferta/Contrato", "Pedido/OT", "Acta", "Permiso", "Certificado",
        "Manual", "Ficha Técnica", "Plano", "PRL/CAE", "Seguro",
        "Albarán", "Factura", "Homologación", "As-Built", "Otros",
    ],
    "estado_documento": [
        "No procede", "Solicitada", "Pendiente", "En revisión",
        "Completada", "Rechazada", "Caducada",
    ],
    "estado_plano": ["Solicitado", "En proceso", "Recibido", "Aprobado", "Obsoleto"],
    "disciplina_plano": [
        "Arquitectura", "Eléctrica", "Seguridad/CCTV", "Intrusión",
        "Control de Accesos", "Redes/Datos", "Contraincendios", "Mecánica",
        "Canalizaciones", "As-Built", "Otros",
    ],
    # ------------------------------------------------------ económico/ofertas
    "estado_oferta": [
        "Borrador", "Pendiente de enviar", "Enviada", "En negociación",
        "Aprobada", "Rechazada", "Facturada",
    ],
    "motivo_ampliacion": [
        "Ampliación de alcance", "Cambio solicitado por cliente",
        "Imprevisto técnico", "Normativa", "Error de proyecto",
        "Condiciones de obra", "Otros",
    ],
    "categoria_coste": [
        "Mano de obra", "Material", "Subcontrata", "Maquinaria",
        "Ampliación", "Desplazamientos", "Incidencias/Imprevistos", "Otros",
    ],
    # --------------------------------------------------------------- visitas
    "tipo_visita": [
        "Replanteo", "Seguimiento", "Coordinación", "Inspección PRL",
        "Recepción/Entrega", "Comercial", "Resolución de incidencia",
        "Pruebas CRA", "Otros",
    ],
    # -------------------------------------------------------------- partes
    "meteorologia": ["Despejado", "Nublado", "Lluvia", "Viento fuerte", "Nieve", "Calor extremo"],
    # ------------------------------------------------------------- contactos
    "tipo_contacto": [
        "Cliente", "Interlocutor Telefónica", "Subcontrata", "Proveedor",
        "CRA", "Mantenimiento", "Propiedad", "Seguridad del centro",
        "Coordinador PRL", "Ingeniería", "Otros",
    ],
    # ------------------------------------------------------------- genéricos
    "si_no": ["Sí", "No"],
    "si_no_np": ["Sí", "No", "No procede"],
}

# Clientes habituales: Telefónica es el caso normal del usuario.
CLIENTES_SUGERIDOS = [
    "Telefónica Soluciones", "Telefónica de España", "Telefónica Empresas",
    "Movistar", "Otros",
]

# Zonas típicas de una nave logística, para el desplegable de ubicación.
ZONAS_SUGERIDAS = [
    "Muelles de carga", "Muelles de descarga", "Playa de camiones",
    "Almacén - Pasillo", "Almacén - Estanterías", "Zona de picking",
    "Zona de packing", "Cámara frigorífica", "Sala técnica / CPD",
    "Sala de seguridad / CRA local", "Oficinas", "Sala de reuniones",
    "Vestuarios", "Comedor", "Acceso peatonal", "Acceso vehicular",
    "Torno de entrada", "Barrera de acceso", "Perímetro Norte",
    "Perímetro Sur", "Perímetro Este", "Perímetro Oeste", "Parking",
    "Cubierta", "Cuarto eléctrico", "Zona de residuos", "Surtidor / GLP",
]

# Estructura de carpetas de obra que se crea en disco al dar de alta una obra.
ESTRUCTURA_CARPETAS = [
    ("00_Oferta y Contrato", "Oferta económica, contrato firmado, pedido/OT, condiciones"),
    ("01_Documentacion Tecnica", "Fichas técnicas, manuales, certificados CRA, homologaciones"),
    ("02_Planos", "Arquitectura, eléctrico, seguridad/CCTV, redes — todas las revisiones"),
    ("03_Subcontratas", "Contratos, seguros RC, documentación PRL/CAE, facturas"),
    ("04_Materiales y Albaranes", "Albaranes de recepción, pedidos, facturas de proveedores"),
    ("05_Maquinaria", "Contratos de alquiler, ITV, certificados de PEMP y andamios"),
    ("06_Personal", "Contratos, PRL, control de accesos, partes de horas"),
    ("07_Actas y Visitas", "Actas de reunión e informes de visita de obra"),
    ("08_Ampliaciones", "Ofertas de ampliación y aprobaciones del cliente"),
    ("09_Facturacion", "Facturas emitidas, certificaciones, justificantes de cobro"),
    ("10_Fotografias", "Reportaje fotográfico de avance e instalación"),
    ("11_Inventario", "Inventario de instalación, etiquetado, direccionamiento IP"),
    ("12_Pruebas y CRA", "Protocolos de prueba, reporte de pruebas CRA, actas de test"),
    ("13_Cierre de Obra", "Acta de recepción, garantías, documentación as-built"),
]


def catalogo(nombre: str) -> list[str]:
    return list(CATALOGOS.get(nombre, []))
