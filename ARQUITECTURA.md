# Arquitectura

Este documento sirve para dos cosas: entender por qué está montado así y poder
cambiarlo dentro de seis meses sin releerlo todo.

---

## La decisión de fondo: una definición, cuatro salidas

Casi todo el valor está en [`app/schema.py`](app/schema.py). Cada entidad se
declara una vez y de ahí salen automáticamente:

1. **La tabla SQLite** — la crea `db.init()` a partir de los campos.
2. **La API REST** — `/api/e/{entidad}` sirve cualquier entidad registrada.
3. **El formulario y la tabla del frontend** — el navegador pide `/api/meta` y
   construye la interfaz; no hay ni un formulario escrito a mano.
4. **La exportación a Excel** — una hoja por entidad, con sus etiquetas y formatos.

Añadir un campo nuevo son tres líneas:

```python
F("num_precinto", "Nº de precinto", list=True, group="Identificación",
  help="Precinto de garantía del fabricante"),
```

Al reiniciar, la columna se crea sola en la base de datos, aparece en el
formulario, se puede buscar y sale en el Excel. **Sin migraciones a mano y sin
tocar el frontend.**

### Añadir un módulo entero

1. Declarar la `Entity` en `schema.py` y añadirla a `ENTITIES`.
2. Añadir la clave a `MENU`.
3. Añadir una línea en `construirMenu()` de [`app/web/js/app.js`](app/web/js/app.js).

Ya tiene alta, edición, borrado, búsqueda, adjuntos, exportación y aparece en
los informes.

---

## Por qué SQLite y no PostgreSQL

Un jefe de obra, unas cuantas obras a la vez, unos miles de registros por obra.
SQLite es un fichero que se copia arrastrándolo, funciona sin servidor, y en este
volumen de datos es más rápido que cualquier alternativa por red.

El modo WAL permite lecturas concurrentes mientras se escribe, que es justo el
patrón de uso: alguien apuntando en el móvil mientras otro consulta en el PC.

**Migración aditiva:** al arrancar se comparan las columnas reales con las
declaradas y se hace `ALTER TABLE ADD COLUMN` de las que falten. Nunca se borra
ni se renombra nada. Actualizar la aplicación no puede destruir datos, ni aunque
se salte diez versiones.

---

## Por qué PWA y no una app nativa

Fue la decisión con más peso del proyecto.

Una app nativa de iPhone exige cuenta de desarrollador de Apple (99 $/año), un
Mac para compilar y pasar por la revisión de la App Store en cada cambio. Para
una herramienta de uso interno, es un peaje sin contrapartida.

Una PWA se instala desde Safari con «Añadir a pantalla de inicio»: icono propio,
pantalla completa, sin barra de navegador. El mismo código sirve para PC,
Android y tablet. Y se actualiza recargando, sin pasar por ninguna tienda.

Lo que se pierde: notificaciones push en iOS son limitadas, y no hay acceso a
Bluetooth ni NFC. Nada de eso hace falta aquí.

Detalles concretos que hacen que se sienta como una app en iPhone:

| Detalle | Por qué |
|---|---|
| `font-size: 16px` en los `input` | Por debajo de eso, Safari hace zoom al enfocar y descoloca la pantalla |
| `viewport-fit=cover` + `env(safe-area-inset-*)` | Que el notch y la barra inferior no tapen contenido |
| `apple-mobile-web-app-capable` | Pantalla completa de verdad al abrir desde el icono |
| `capture="environment"` en el input de foto | Abre directamente la cámara trasera, sin pasar por la galería |
| Compresión de imagen en el navegador | Una foto de iPhone son 4 MB; en obra hay mala cobertura |
| Áreas táctiles de 42 px mínimo | Se usa de pie, con prisa y a veces con guantes |

---

## Por qué JavaScript sin framework

No hay `npm install`, ni `node_modules`, ni paso de compilación. Se edita un
`.js` y se recarga. Dentro de dos años seguirá funcionando igual, sin que ninguna
dependencia se haya roto ni pida migrar a la versión siguiente.

El coste es escribir el DOM a mano, que se lleva bien con la función `el()` de
[`ui.js`](app/web/js/ui.js). Y como la interfaz se genera desde los metadatos, hay
mucho menos código del que parecería.

Los módulos:

| Archivo | Responsabilidad |
|---|---|
| `api.js` | Único punto de acceso al servidor. Centraliza errores y sesión caducada. |
| `ui.js` | `el()`, modales, avisos, formato de euros y fechas, semáforos de estado. |
| `estado.js` | Estado compartido: metadatos, obra activa, cachés. |
| `forms.js` | Generación y validación de formularios desde los metadatos. |
| `views.js` | Cuadro de mando, listados, ficha de detalle, Gantt, económico. |
| `ia.js` | Cámara, escáner de etiquetas y albaranes, asistente. |
| `ajustes.js` | Ajustes, plantillas, importación, copias de seguridad. |
| `app.js` | Arranque, sesión, enrutado, menú. |

---

## El motor de alertas

Está en [`app/services/kpis.py`](app/services/kpis.py) y es lo que separa esto de
una hoja de cálculo. Cada regla tiene severidad, un mensaje con el dato concreto
y el módulo donde se arregla.

Se recalcula en cada carga en vez de guardarse. Con este volumen de datos cuesta
milisegundos, y evita el problema clásico de las alertas persistidas: quedarse
obsoletas y perder la confianza del usuario.

Añadir una regla:

```python
if condicion:
    add("alta", "Título corto y concreto",
        "Qué está pasando y qué hay que hacer al respecto.",
        "modulo_donde_se_arregla", cuantos)
```

Las severidades son `critica`, `alta`, `media` e `info`, y se ordenan solas.

**Criterio de diseño:** una alerta que no lleva a una acción es ruido. Cada
mensaje dice qué pasa *y* qué hacer. Y se avisa antes de que el problema exista
—ITV a 30 días, seguro a 30 días— porque cuando ya ha ocurrido no es una alerta,
es un parte de daños.

---

## La integración con la IA

Tres funciones en [`app/services/ai.py`](app/services/ai.py), todas contra la API
de Anthropic con `claude-opus-5`.

**Extracción estructurada, no texto libre.** La lectura de etiquetas usa
`output_config.format` con un esquema JSON: la respuesta viene ya validada contra
la forma esperada, sin parsear texto ni rezar para que el modelo devuelva JSON
correcto.

**El prompt asume el oficio.** No dice «extrae texto de esta imagen», sino que
eres el jefe de obra dando de alta material en el inventario. Eso hace que
clasifique un `DS-2CD2686G2-IZS` como cámara IP bullet aunque la etiqueta no lo
diga.

**Prohibido inventar.** El prompt insiste en que un dato que no se lee vuelve
vacío, y que si un carácter es ambiguo (0/O, 1/I, 5/S, 8/B) hay que marcar
confianza baja y decir cuál. Un número de serie inventado es peor que ninguno:
se descubre el día que hay que tramitar una garantía.

**Degradación limpia.** Sin clave de API, `ai.disponible()` devuelve `False`, el
frontend oculta las funciones y explica cómo activarlas. Nada más se rompe.

---

## Seguridad

| Riesgo | Mitigación |
|---|---|
| App publicada sin contraseña | Con `OBRASEC_PUBLIC=1` se niega a arrancar sin ella |
| Contraseñas en claro | PBKDF2-SHA256, 240 000 iteraciones, sal por contraseña |
| Robo de sesión | Cookie `httponly` + `samesite=lax`, `secure` en modo público |
| Path traversal en subidas | Nombres saneados a ASCII y `Path.name`; ruta fija |
| Inyección SQL | Consultas parametrizadas siempre; los nombres de tabla salen del registro, no del usuario |
| Fuga de datos por descarga | Todas las rutas exigen sesión |
| Contraseñas de equipos | El inventario guarda *dónde está* la contraseña, no la contraseña |

Ese último punto es deliberado. El campo se llama «Referencia de contraseña» y
la ayuda dice explícitamente que no se pegue ahí la contraseña del NVR. Una base
de datos con las credenciales de todos los grabadores de un cliente es un
problema serio el día que se filtra.

---

## Qué no está hecho

Con honestidad, porque saberlo importa más que la lista de lo que sí:

- **Sin edición concurrente real.** Si dos personas editan el mismo registro a la
  vez, gana el último. Para un jefe de obra y su equipo no es un problema; para
  una oficina técnica de diez personas, habría que añadir control de versión por
  registro.
- **Sin modo offline de escritura.** El service worker cachea la interfaz, así
  que la app abre sin cobertura, pero guardar necesita conexión. Una nave con
  zonas sin cobertura pide una cola local de escrituras con sincronización
  posterior. Es el siguiente paso natural.
- **Sin multiusuario.** Una contraseña, un usuario. Añadir roles (jefe de obra,
  técnico, administración) sería un cambio de calado en `auth.py` y en cada ruta.
- **Sin firma digital en las actas.** Se generan en Word y se firman fuera.
- **Gantt sin dependencias visuales.** El campo `depende_de` se guarda y se puede
  consultar, pero el diagrama no dibuja las flechas ni recalcula fechas en
  cascada.
