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


# Credenciales oficiales que NO tenemos. El producto no emite e-CF: no firma XML, no
# transmite al webservice y no esta autorizado por la DGII (routes/accounting.js:1701 de
# la app lo dice: la serie E se admite solo para REGISTRAR lo que el cliente ya emitio con
# un sistema certificado). El 16-ago-2026 el blog afirmaba lo contrario en 3 paginas:
# "software autorizado por la DGII", "carga de tu certificado INDOTEL" y "acompanamiento
# en el set de pruebas". Inventarse un sello de un organismo publico es de lo peor que
# puede decir el sitio.
#
# No se pueden prohibir a secas: el sitio EXPLICA el proceso de la DGII y ahi las mismas
# frases son ciertas ("elige tu software autorizado por la DGII"). Lo que no vale es
# decirlas de NOSOTROS, asi que solo saltan si "MisCuentas" esta cerca.
# Grupo 1: frases que SOLO se pueden estar diciendo de nosotros. El articulo explica el
# proceso hablandole al lector de "un certificado", nunca de "carga directa de TU
# certificado"; describe el webservice con el verbo ("transmitirlo al webservice"), no con
# nuestro sustantivo de folleto. Por eso basta con que "MisCuentas" ande cerca.
VENTANA_MISCUENTAS = 400
PROHIBIDO_CERCA_DE_MISCUENTAS = [
    (r"emisi[oó]n\s+autom[aá]tica\s+de\s+e-?CF", "no emitimos e-CF, solo registramos los ajenos"),
    (r"(?:carga|subida)\s+(?:directa\s+)?de\s+tu\s+certificado", "no existe la carga de certificado INDOTEL"),
    (r"set\s+de\s+pruebas\s+de\s+certificaci[oó]n", "no acompanamos el set de pruebas"),
    (r"transmisi[oó]n\s+al\s+webservice", "no transmitimos nada a la DGII"),
    (r"firma\s+digital\s+y\s+transmisi[oó]n", "no firmamos ni transmitimos nada"),
]

# Grupo 2: las mismas palabras son CIERTAS explicando el proceso ("elige tu software
# autorizado por la DGII"), asi que aqui la ventana de 400 daba 6 falsos positivos: cazaba
# el texto educativo y, peor, cazaba nuestras propias negaciones ("MisCuentas NO es un
# software autorizado por la DGII"). Un guardian que grita en la frase honesta acaba
# desactivado. Se exige que "MisCuentas" este en la MISMA frase y que esa frase no la
# niegue.
PROHIBIDO_AFIRMADO_DE_MISCUENTAS = [
    (r"autorizad[oa]\s+por\s+la\s+DGII", "credencial que no tenemos: la DGII no nos autorizo"),
    (r"homologad[oa]", "credencial que no tenemos"),
    (r"certificad[oa]s?\s+para\s+emitir", "credencial que no tenemos"),
    (r"(?:preparado|listo)s?\s+para\s+(?:la\s+emisi[oó]n\s+de\s+)?el?\s*e-?CF", "insinua una capacidad que no existe"),
]
NEGACION = re.compile(r"\b(?:no|nunca|todav[ií]a\s+no|a[uú]n\s+no|sin)\b", re.I)


def frase_de(texto, ini, fin):
    """El trozo de texto alrededor de la coincidencia, sin marcado y sin cruzar puntos.

    Los limites son el punto, los signos de cierre y las etiquetas de bloque: un <li> es
    una frase aunque no lleve punto final.
    """
    izq = max(
        (texto.rfind(c, 0, ini) for c in (". ", "! ", "? ", "<li", "<p", "<h", "<td", "<tr")),
        default=-1)
    der = min(
        (p for p in (texto.find(c, fin) for c in (". ", "! ", "? ", "</li", "</p", "</h", "</td"))
         if p != -1),
        default=len(texto))
    return re.sub(r"<[^>]+>", " ", texto[izq + 1:der])


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

    for patron, motivo in PROHIBIDO_CERCA_DE_MISCUENTAS:
        for m in re.finditer(patron, t, re.I):
            ventana = t[max(0, m.start() - VENTANA_MISCUENTAS):m.end() + VENTANA_MISCUENTAS]
            if "MisCuentas" in ventana:
                fallos.append(f"{rel}: {m.group(0)!r} dicho de MisCuentas — {motivo}")

    for patron, motivo in PROHIBIDO_AFIRMADO_DE_MISCUENTAS:
        for m in re.finditer(patron, t, re.I):
            frase = frase_de(t, m.start(), m.end())
            if "MisCuentas" in frase and not NEGACION.search(frase):
                fallos.append(f"{rel}: {m.group(0)!r} afirmado de MisCuentas — {motivo}")

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
