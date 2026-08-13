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
]


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

    if any(v in t for v in PRECIOS.values()):
        paginas_con_precio += 1

    # el marcado JSON-LD tiene que ser valido y no contradecir a la pagina
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            json.loads(m.group(1))
        except json.JSONDecodeError as e:
            fallos.append(f"{rel}: JSON-LD invalido ({e})")

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
