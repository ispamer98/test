# Publicar ObraSec en tu dominio

Con ObraSec corriendo sólo en el PC, el móvil funciona pero **sólo dentro de la
misma Wi-Fi**. En una nave de Illescas, con el portátil apagado en la oficina,
no hay nada.

Publicándolo en un subdominio propio —por ejemplo `obra.tudominio.uk`— lo tienes
desde cualquier sitio, con datos móviles, y el iPhone lo instala igual que una
app del App Store.

> **Antes de nada:** en cuanto sale a internet, **la contraseña es obligatoria**.
> ObraSec se niega a arrancar en modo público sin ella. No es una molestia: son
> los precios, los clientes y los planos de seguridad de naves reales.

---

## Opción A · Cloudflare Tunnel (recomendada)

El túnel abre una conexión **de salida** desde tu máquina hacia Cloudflare. No
hay que abrir puertos en el router, ni exponer la IP de casa, ni pelearse con la
IP dinámica. Y Cloudflare pone el certificado HTTPS, que además hace falta para
que la cámara funcione en el móvil.

### 1. Crear el túnel

En el panel de Cloudflare:

1. **Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel**
2. Tipo **Cloudflared**. Ponle un nombre, por ejemplo `obrasec`.
3. Copia el **token** que aparece (una cadena larga que empieza por `eyJ…`).
4. En **Public Hostnames**, añade:

   | Campo | Valor |
   |---|---|
   | Subdomain | `obra` |
   | Domain | `tudominio.uk` |
   | Service Type | `HTTP` |
   | URL | `obrasec:8321` |

   `obrasec` es el nombre del contenedor: dentro de la red de Docker se resuelve
   solo, sin tocar IPs.

### 2. Configurar y arrancar

```bash
git clone https://github.com/ispamer98/test.git obrasec
cd obrasec
cp .env.ejemplo .env
```

Edita `.env`:

```bash
OBRASEC_PASSWORD=una-contraseña-larga-que-solo-sepas-tú
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiXXXXXXXX…
ANTHROPIC_API_KEY=sk-ant-…      # opcional
```

Y arranca:

```bash
docker compose up -d
```

Ya está. `https://obra.tudominio.uk` funciona desde cualquier parte.

### 3. Instalarlo en el iPhone

Safari → `https://obra.tudominio.uk` → **Compartir** → **Añadir a pantalla de
inicio**. Con HTTPS, la cámara y el escáner de etiquetas funcionan igual que en
una app nativa.

### 4. Cerrarlo aún más (opcional pero recomendable)

En **Zero Trust → Access → Applications**, crea una aplicación que cubra
`obra.tudominio.uk` con una política de tipo *Email OTP* limitada a tu correo.
Así Cloudflare pide un código antes incluso de llegar a ObraSec: dos cerraduras
en vez de una, y los bots ni ven la pantalla de acceso.

---

## Convivencia con tus proyectos de Reflex

Si ya tienes cosas desplegadas en ese dominio, **no se pisan**. Cada aplicación
va en su propio subdominio y su propio Public Hostname dentro del mismo túnel:

| Hostname | Service |
|---|---|
| `app1.tudominio.uk` | `http://reflex1:3000` |
| `app2.tudominio.uk` | `http://reflex2:3000` |
| `obra.tudominio.uk` | `http://obrasec:8321` |

Si tus proyectos de Reflex ya corren en Docker, mete el servicio `obrasec` del
[`docker-compose.yml`](docker-compose.yml) en tu compose existente y añade sólo
el Public Hostname nuevo; el `cloudflared` que ya tienes vale.

Un aviso: si tus contenedores están en redes de Docker distintas, `cloudflared`
no verá a `obrasec`. O los pones en la misma red, o le das al servicio
`obrasec` una entrada en la red donde vive el túnel.

---

## Opción B · Sin Docker

Con Python en el servidor:

```bash
pip install -r requirements.txt
export OBRASEC_PUBLIC=1
export OBRASEC_PASSWORD='tu-contraseña-larga'
export OBRASEC_DATA=/var/lib/obrasec
uvicorn app.main:app --host 127.0.0.1 --port 8321 --proxy-headers
```

Escucha sólo en `127.0.0.1`: nadie llega directamente, sólo a través del túnel o
del proxy inverso. Luego `cloudflared tunnel run --token …`, o un Nginx delante.

Para que sobreviva a los reinicios, `systemd`:

```ini
# /etc/systemd/system/obrasec.service
[Unit]
Description=ObraSec
After=network.target

[Service]
User=obrasec
WorkingDirectory=/opt/obrasec
Environment=OBRASEC_PUBLIC=1
Environment=OBRASEC_DATA=/var/lib/obrasec
EnvironmentFile=/etc/obrasec.env
ExecStart=/opt/obrasec/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8321 --proxy-headers
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now obrasec
```

---

## Opción C · Sólo tu Wi-Fi

Si no quieres nada en internet, no lo publiques: en la oficina y con el PC
encendido, el QR del arranque ya te da acceso desde el móvil. Es la opción más
privada — los datos no salen de tu red — a cambio de depender de que el PC esté
encendido.

---

## Copias de seguridad en un despliegue

Los datos viven en el volumen `obrasec-datos`. Copia semanal:

```bash
docker run --rm \
  -v obrasec-datos:/datos:ro \
  -v "$PWD":/salida \
  alpine tar czf /salida/obrasec-$(date +%F).tar.gz -C /datos .
```

O más simple: entra en la app y usa **Ajustes → Descargar copia**, que genera un
ZIP con base de datos, fotos y plantillas.

---

## Actualizar

```bash
cd obrasec
git pull
docker compose up -d --build
```

Las columnas nuevas se añaden solas al arrancar y **nunca se borra ninguna**, así
que actualizar no pierde datos. Aun así, haz la copia antes: es un minuto.

---

## Comprobaciones de seguridad

Antes de dar por buena la publicación:

- [ ] `https://obra.tudominio.uk` pide contraseña
- [ ] La contraseña tiene más de 12 caracteres y no la usas en ningún otro sitio
- [ ] El archivo `.env` **no** está subido a GitHub (lo cubre el `.gitignore`)
- [ ] `docker compose ps` no muestra ningún puerto publicado en el host
- [ ] Tienes una copia de seguridad descargada y guardada fuera del servidor
- [ ] Si añadiste Cloudflare Access, has probado a entrar desde el móvil
