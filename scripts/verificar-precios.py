#!/usr/bin/env python3
"""Comprueba que el precio publicado sea el mismo en todo el sitio.

Por que existe: en agosto de 2026 el precio estaba copiado a mano en 30 sitios de 6
paginas. La landing decia RD$990 y la app cobraba US$19 (~RD$1,100), y nadie lo vio
hasta que lo encontro un informe externo. Mientras el precio siga escrito a mano en
cada pagina, esto se vuelve a descolocar: esto es lo que lo caza.

Uso:  python3 scripts/verificar-precios.py     (0 = todo coherente, 1 = hay que mirar)
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# El precio publico. Si cambia, se cambia AQUI y el script dira que paginas quedaron atras.
PRECIOS = {"Básico": "US$19", "Pro": "US$49"}

# Lo mismo pero como lo escribe el JSON-LD: sin simbolo, y el 0 del plan Free.
MONEDA = "USD"
PRECIOS_SCHEMA = {"0"} | {v.removeprefix("US$") for v in PRECIOS.values()}


def ofertas_de(nodo):
    """Todas las Offer del documento, esten sueltas, en lista o dentro de @graph."""
    if isinstance(nodo, dict):
        if nodo.get("@type") == "Offer":
            yield nodo
        for valor in nodo.values():
            yield from ofertas_de(valor)
    elif isinstance(nodo, list):
        for elemento in nodo:
            yield from ofertas_de(elemento)

# Lo que no puede aparecer: precios viejos y argumentos que ya no son ciertos.
PROHIBIDO = [
    ("RD$990", "precio viejo en pesos del plan Basico"),
    ("RD$2,490", "precio viejo en pesos del plan Pro"),
    ("precio fijo en DOP", "argumento de moneda: ya se cobra en dolares"),
    ("cobra en pesos dominicanos", "argumento de moneda: ya se cobra en dolares"),
    ("Precio en pesos dominicanos", "argumento de moneda: ya se cobra en dolares"),
    ("sin variaciones por el tipo de cambio", "argumento de moneda: ya se cobra en dolares"),
    ("add-on RD$300", "el 606/607 no esta cerrado por plan: /api/dgii/* no lo cobra"),
    ("Usuarios ilimitados", "Pro tiene max_users: 3 en planPermissions.js"),
    ("Todos los reportes DGII", "606/607/608 no estan cerrados por plan: son iguales en Free, Basico y Pro"),
    ("Reconciliación bancaria", "/api/conciliacion* solo lleva authMiddleware: la tienen todos los planes"),
]

# Lo mismo, pero cuando la frase se puede escribir de diez maneras. La lista de arriba
# tenia "cobra en pesos dominicanos" exacto y el articulo de la comparativa decia "cobre
# en pesos": se colo por una conjugacion y estuvo meses atacando a Alegra por cobrar en
# dolares, que es justo lo que hacemos nosotros.
PROHIBIDO_REGEX = [
    (r"cobr\w*\s+(?:\w+\s+){0,3}?en\s+pesos", "argumento de moneda: solo se cobra en USD"),
    (r"precios?\s+(?:reales?|fijos?)\s+en\s+pesos", "argumento de moneda: solo se cobra en USD"),
]


DOMINIO = "https://miscuentasrd.com"
# href/src/content que apuntan a un fichero nuestro. Se ignoran anclas, mailto,
# tel, data: y todo lo que viva en otro dominio.
REF_ASSET = re.compile(r'(?:href|src|content)="([^"]+\.(?:png|jpg|jpeg|webp|avif|svg|ico|css|js|pdf))"', re.I)


# El JSON-LD referencia imagenes sin href/src/content ("screenshot": [...], "image": ...)
# y ahi vivia la mitad de los assets del sitio, sin comprobar. Hasta el 16-ago-2026
# apuntaban a raw.githubusercontent.com, que depende de que el repo siga publico.
REF_JSONLD = re.compile(r'"(?:https?://[^"]+\.(?:png|jpg|jpeg|webp|avif|svg|ico))"', re.I)


def referencias_locales(texto):
    candidatas = REF_ASSET.findall(texto) + [
        u.strip('"') for u in REF_JSONLD.findall(texto)
    ]
    for ref in candidatas:
        if ref.startswith(DOMINIO):
            ref = ref[len(DOMINIO):]
        elif "//" in ref or ref.startswith(("data:", "mailto:", "tel:", "#")):
            continue
        # /cdn-cgi/ lo inyecta y lo sirve Cloudflare, no vive en el repo.
        if ref.startswith("/cdn-cgi/"):
            continue
        yield ref


def htmls():
    for raiz, dirs, ficheros in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "graphify-out")]
        for f in ficheros:
            if f.endswith(".html") and ".bak" not in f:
                yield os.path.join(raiz, f)


fallos = []
paginas_con_precio = 0

for ruta in htmls():
    rel = os.path.relpath(ruta, RAIZ)
    t = open(ruta, encoding="utf-8", errors="replace").read()

    for texto, motivo in PROHIBIDO:
        if texto in t:
            fallos.append(f"{rel}: aparece {texto!r} — {motivo}")

    for patron, motivo in PROHIBIDO_REGEX:
        for m in re.finditer(patron, t, re.I):
            fallos.append(f"{rel}: aparece {m.group(0)!r} — {motivo}")

    # Que el fichero que la pagina promete exista de verdad. Hasta el 16-ago-2026
    # dos paginas anunciaban /screenshots/og.png y 13 pedian /favicon.ico: los dos
    # devolvian 404. Una imagen social rota no se ve al mirar la pagina, solo al
    # compartirla, asi que nadie lo nota.
    for ref in referencias_locales(t):
        destino = os.path.join(RAIZ, ref.lstrip("/")) if ref.startswith("/") \
            else os.path.normpath(os.path.join(os.path.dirname(ruta), ref))
        if not os.path.exists(destino):
            fallos.append(f"{rel}: apunta a {ref} y ese fichero no existe")

    if any(v in t for v in PRECIOS.values()):
        paginas_con_precio += 1

    # el marcado JSON-LD tiene que ser valido y no contradecir a la pagina
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            datos = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            fallos.append(f"{rel}: JSON-LD invalido ({e})")
            continue

        # Que PARSEE no basta: hasta el 16-ago-2026 el schema publicaba 990 y 2490 en DOP
        # mientras la pagina cobraba US$19 y US$49, y este script daba verde. Google lee el
        # schema, no el texto: una oferta que contradice a la pagina es precio falso.
        for oferta in ofertas_de(datos):
            precio = str(oferta.get("price", "")).strip()
            moneda = str(oferta.get("priceCurrency", "")).strip()
            nombre = oferta.get("name") or "sin nombre"
            if moneda and moneda != MONEDA:
                fallos.append(
                    f"{rel}: JSON-LD oferta {nombre!r} en {moneda} — solo se cobra en {MONEDA}")
            if precio and precio not in PRECIOS_SCHEMA:
                fallos.append(
                    f"{rel}: JSON-LD oferta {nombre!r} con price={precio!r} — "
                    f"los precios reales son {sorted(PRECIOS_SCHEMA)}")

    # una MENSUALIDAD en dolares que no sea una de las nuestras. Se exige el "/mes" a
    # proposito: el sitio menciona cifras en dolares que no son precios (tasas, multas),
    # y marcarlas seria ruido. Los precios de competidores van como USD$29, no US$29.
    for m in re.finditer(r"US\$(\d+)\s*/\s*mes", t):
        if f"US${m.group(1)}" not in PRECIOS.values():
            ctx = re.sub(r"\s+", " ", t[max(0, m.start() - 70):m.start() + 40])
            fallos.append(f"{rel}: mensualidad US${m.group(1)}/mes desconocida — ...{ctx.strip()}...")

if paginas_con_precio == 0:
    fallos.append("ninguna pagina publica el precio: algo se borro de mas")

if fallos:
    print(f"✗ {len(fallos)} problema(s):")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)

print(f"✓ precio coherente en las {paginas_con_precio} paginas que lo publican "
       f"({' · '.join(f'{k} {v}' for k, v in PRECIOS.items())})")
