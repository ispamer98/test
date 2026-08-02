<div align="center">

# 🏗️ ObraSec

**Gestor integral de obra para instalaciones de seguridad**

CCTV · Intrusión · Control de accesos · Redes — en naves logísticas

Funciona en PC, tablet y iPhone. Con inteligencia artificial para dar de alta
equipos a partir de una foto de la etiqueta.

</div>

---

## Qué resuelve

Un jefe de obra de instalaciones de seguridad no lleva una obra: lleva varias a
la vez, cada una con su cliente, su subcontrata, su material y sus plazos. El
Excel se queda corto en cuanto entra el segundo instalador, y lo que se pierde
no son datos: son certificaciones sin cobrar, seguros caducados y actas que no
se pueden firmar porque falta el inventario.

ObraSec es ese Excel, pero que además **avisa**.

| | |
|---|---|
| 📊 **Cuadro de mando** | Avance, plazo, margen y alertas de un vistazo |
| ⚠️ **Alertas de jefe de obra** | Reglas que vigilan lo que se te puede escapar |
| 📹 **Inventario de instalación** | Ficha por equipo: S/N, MAC, IP, VLAN, puerto de switch, pruebas |
| 📷 **Alta por foto** | Fotografía la etiqueta y la IA rellena marca, modelo, nº de serie y MAC |
| 📋 **Albaranes por foto** | Fotografía el albarán y el material entra en el almacén |
| ✨ **Asistente** | «¿Vamos a llegar a la fecha?» respondido con tus datos reales |
| 📅 **Calendario** | Gantt automático a partir de las fechas de las tareas |
| 💶 **Económico** | Presupuestado vs. real, margen, certificaciones y cobros |
| 📄 **Informes** | Con **tus** plantillas de Word, conservando tu membrete |
| 📊 **Excel** | Exportación con portada, cuadro de mando y una hoja por módulo |
| 📥 **Importación** | Lee tus libros «Control de Obra» actuales sin perder nada |
| 📸 **Evidencias** | Fotos por equipo, por tarea y por incidencia |

---

## Instalación

### Windows — la vía rápida

1. Descarga **`ObraSec.exe`** de la [última versión](../../releases/latest).
2. Doble clic.
3. Se abre el navegador. Ya está.

No necesita Python, ni instalador, ni permisos de administrador.

### Cualquier sistema — desde el código

```bash
git clone https://github.com/ispamer98/test.git obrasec
cd obrasec
python run.py
```

La primera vez instala lo que necesita. A partir de ahí arranca en dos segundos.

---

## Móvil y tablet

Al arrancar, la consola muestra una dirección y un **código QR**:

```
  En este ordenador:   http://localhost:8321
  Móvil y tablet:      http://192.168.1.40:8321
```

### iPhone y iPad

1. Abre esa dirección **en Safari** (tiene que ser Safari, no Chrome).
2. Botón **Compartir** → **Añadir a pantalla de inicio**.
3. Aparece el icono de ObraSec como una app más.

Desde ahí funciona a pantalla completa, sin barra de navegador, y la cámara se
abre directamente al pulsar «Escanear». Es una PWA: no hace falta App Store, ni
cuenta de desarrollador de Apple, ni esperar a que Apple apruebe nada.

### Android

Igual, pero en Chrome: menú **⋮** → **Instalar aplicación**.

> **Requisito:** el móvil y el PC en la misma red Wi-Fi. Para usarla desde
> cualquier sitio (una obra en Illescas, el AVE, casa del cliente), mira
> [DESPLIEGUE.md](DESPLIEGUE.md).

---

## Inteligencia artificial

Opcional. Sin ella la aplicación funciona entera; con ella se ahorra la mayor
parte del tecleo en obra.

1. Consigue una clave en [console.anthropic.com](https://console.anthropic.com/settings/keys).
2. ObraSec → **Ajustes → Inteligencia artificial** → pega la clave.

Entonces puedes:

**📷 Dar de alta un equipo con una foto.** Pulsa «Escanear» en la barra
inferior, enfoca la etiqueta de la cámara y la IA extrae marca, modelo, número
de serie, MAC, part number, alimentación PoE y resolución. Interpreta de qué
tipo de equipo se trata y lo clasifica solo. Si la foto está borrosa te lo dice
y te señala qué carácter es dudoso, en lugar de inventárselo.

**📋 Recepcionar material con una foto.** Fotografía el albarán y salen las
líneas de material. Marcas las que entran y se suman al stock; si el material ya
existía, se acumula la cantidad en vez de duplicarlo.

**✨ Preguntar por la obra.** «¿Qué debería vigilar hoy?», «¿dónde se me está
yendo el dinero?», «¿qué me falta para firmar el acta?». Responde con los datos
reales de la base, no con generalidades.

La clave se guarda **sólo en tu equipo**. Las fotos van a la API de Anthropic
para analizarlas y no se usan para entrenar modelos.

---

## Informes con tus plantillas

Sube tu documento de Word con tu membrete en **Ajustes → Plantillas**. Donde
quieras un dato, escribe su marcador:

```
INFORME DE SEGUIMIENTO

Obra:     {{ obra.nombre }}
Cliente:  {{ obra.cliente }}          OT: {{ obra.codigo }}
Avance:   {{ kpi.avance }} %          Margen: {{ economico.margen_pct }} %

Equipos instalados: {{ kpi.dispositivos_instalados }} de {{ kpi.dispositivos_total }}
```

Para repetir las filas de una tabla hacen falta **tres filas**: una sólo con la
apertura del bucle, otra con los datos y otra sólo con el cierre. Las dos filas
de control desaparecen al generar el informe.

| Etiqueta | Modelo | Nº serie | IP |
|---|---|---|---|
| `{%tr for x in dispositivos %}` | | | |
| `{{ x.etiqueta }}` | `{{ x.modelo }}` | `{{ x.num_serie }}` | `{{ x.ip }}` |
| `{%tr endfor %}` | | | |

Para listas fuera de tablas, `{%p for a in alertas %}` en un párrafo suelto y
`{%p endfor %}` en otro.

Tienes una plantilla lista para usar en
[`ejemplos/plantilla-informe-semanal.docx`](ejemplos/plantilla-informe-semanal.docx):
descárgala, cámbiale el membrete y súbela tal cual. La lista completa de
marcadores está en **Ajustes → Ver marcadores disponibles**.

Si no subes ninguna plantilla, ObraSec genera igualmente un informe de
seguimiento completo.

---

## Importar tus Excel actuales

**Ajustes → Importar desde Excel.** Reconoce las hojas por su nombre y las
columnas por su cabecera, así que funciona con los distintos formatos de
«Control de Obra» y con cualquier libro parecido.

Antes de tocar nada te enseña qué va a importar y desde dónde. Y rescata cosas
que se perderían con una importación normal: si apuntabas el material consumido
en la propia fila de la tarea (columnas «Material 1», «Cantidad 1»…), lo
convierte en consumos con su tarea asociada.

---

## Las alertas

Es lo que diferencia esto de una hoja de cálculo. Cada vez que abres el cuadro
de mando se evalúan, entre otras:

- Tareas fuera de plazo, bloqueadas o que vencen en 3 días
- **Desviación entre plazo consumido y avance real** — la que avisa de verdad
- Material bajo mínimo, agotado o con consumo superior al recibido
- Incidencias graves sin cerrar y con fecha límite vencida
- **Subcontratas sin seguro RC o sin PRL/CAE** — si hay un accidente, la
  responsabilidad sube por la cadena de contratación
- Seguros y reconocimientos médicos por caducar
- Personal sin acreditación de acceso
- ITV de PEMP y andamios a menos de 30 días
- **Direcciones IP duplicadas en el inventario** — esas caídas intermitentes que
  cuestan una tarde de diagnóstico
- Equipos instalados sin número de serie o sin pruebas registradas
- Ampliaciones enviadas sin respuesta durante más de 10 días
- Margen por debajo del 10 % o negativo
- Certificaciones con el cobro vencido

Cada alerta lleva su severidad, el dato concreto y un enlace al módulo donde se
arregla.

---

## Copias de seguridad

**Ajustes → Descargar copia** genera un ZIP con la base de datos, las fotos y
las plantillas. Guárdalo fuera del ordenador.

Los datos viven en `C:\Users\<tu usuario>\ObraSec\` (o `~/ObraSec` en Linux y
Mac). Se puede cambiar con `python run.py --datos D:\Obras`.

---

## Documentación

| Documento | Contenido |
|---|---|
| [DESPLIEGUE.md](DESPLIEGUE.md) | Publicarlo en tu dominio con Cloudflare para usarlo desde cualquier sitio |
| [ARQUITECTURA.md](ARQUITECTURA.md) | Cómo está construido y cómo añadir campos o módulos nuevos |

---

## Bajo el capó

Python + FastAPI + SQLite, sin ORM y sin dependencias de más. El frontend es una
PWA en JavaScript sin framework ni paso de compilación: se edita un archivo y ya
está. **Todos los formularios, tablas, exportaciones y validaciones se generan a
partir de un único registro de entidades** ([`app/schema.py`](app/schema.py)), de
modo que añadir un campo son tres líneas y aparece en todas partes.

```
app/
  schema.py       Registro de entidades → BD, API y formularios
  catalogs.py     Listas del dominio (tipos de equipo, estados, zonas…)
  db.py           SQLite con migración aditiva: nunca se pierde una columna
  auth.py         Contraseña única con PBKDF2
  main.py         API REST + servidor de la PWA
  services/
    kpis.py       Cuadro de mando, motor de alertas y Gantt
    ai.py         Visión y asistente (Claude)
    reports.py    Informes Word con plantillas del usuario
    exporter.py   Exportación a Excel con formato
    importer.py   Importación desde libros de control existentes
  web/            La PWA (HTML, CSS y JS sin compilar)
tests/
  test_humo.py    Ciclo completo de una obra, de punta a punta
  test_seguridad.py  Path traversal, inyección SQL, sesiones y secretos
```

Para pruebas:

```bash
python tests/test_humo.py        # ciclo completo de una obra
python tests/test_seguridad.py   # defensas: subidas, SQL, sesión, secretos
```

---

<div align="center">
<sub>Hecho para llevar obras de verdad, no para enseñar en una demo.</sub>
</div>
