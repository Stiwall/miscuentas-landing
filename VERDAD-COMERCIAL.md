# Verdad comercial de MisCuentas

Fuente única de lo que cada plan cobra y permite. **Si esto y la web no coinciden, manda
esto** — y si esto y el código no coinciden, manda el código y hay que corregir este
archivo.

- **Verificado:** 16 de agosto de 2026
- **Contra:** `Stiwall/Miscuentas-Contable-App`, rama `develop`, commit `f716ac2` (14-ago-2026)
- **Ficheros leídos:** `lib/plans.js`, `lib/planPermissions.js`, `routes/reports.js`, `routes/polarCheckout.js`
- **Responsable de mantenerlo al día:** Starlin

Cada vez que se toque un precio, un límite o un permiso de plan en el código, se actualiza
este archivo en el mismo cambio. `scripts/verificar-precios.py` comprueba automáticamente
la parte de precios y moneda.

---

## Precios

| Plan | Precio mensual | Canal |
|---|---:|---|
| Free | 0 | Registro gratuito |
| Starter | RD$299 | WhatsApp |
| Negocio | RD$600 | WhatsApp |
| Contador | RD$1,200 | WhatsApp |
| Básico | US$19 | Pago en línea con Polar |
| Pro | US$49 | Pago en línea con Polar |

La ruta pública `/upgrade` de la app ofrece los planes en pesos con enlaces a WhatsApp.
`routes/polarCheckout.js` admite Básico y Pro en USD mediante `usdPriceFor()`.
El pago en línea admite 1, 3 o 12 meses. Al elegir 12 meses se pagan 10.
Los dos canales se explican en `/precios`.

---

## Límites por plan

De `lib/planPermissions.js`. `null` significa sin límite.

| | Free | Trial (14 días) | Básico | Pro |
|---|---|---|---|---|
| Empresas | 1 | 1 | 1 | **5** |
| Usuarios | 1 | 3 | 1 | **3** |
| Facturas / mes | 30 | sin límite | 300 | sin límite |
| Clientes | 10 | sin límite | sin límite | sin límite |
| Proveedores | 5 | sin límite | sin límite | sin límite |
| Cotizaciones / mes | 5 | sin límite | 50 | sin límite |
| Activos fijos | 3 | sin límite | 20 | sin límite |
| Asientos / mes | 10 | sin límite | sin límite | sin límite |
| Inventario | no | sí | **sí** | sí |
| Reportes avanzados | no | sí | **no** | sí |
| Panel multiempresa | no | no | no | **sí** |
| Soporte | no | — | no | **sí** |

**Pro no es "usuarios ilimitados": son 3.** Y no es "empresas ilimitadas": son 5.

### Qué es "reportes avanzados"

La línea que de verdad separa Básico de Pro, y que hoy **no se nombra en la web**. Tras
`requireFeature('reportes_avanzados')` en `routes/reports.js`:

- Estado de Resultados (`/api/income-statement`)
- Balanza de comprobación (`/api/trial-balance`)
- Libro mayor por cuenta (`/api/account-ledger`)
- Cierre mensual y cierre anual, con sus previsualizaciones e historial
- **Todas las exportaciones CSV**: cuentas, clientes, proveedores, CxC, CxP, diario, transacciones

Es decir: **quien paga Básico no puede sacar un Estado de Resultados ni exportar nada.**

---

## Qué NO está cerrado por plan

Comprobado ruta por ruta en `routes/reports.js`: estas llevan solo `authMiddleware`, así que
funcionan **en todos los planes, Free incluido**.

- **Reportes DGII 606, 607 y 608.** Ningún plan tiene más DGII que otro. Decir "Todos los
  reportes DGII" como ventaja de Pro es falso.
- **Reconciliación bancaria** (`/api/conciliacion`, `/mark`, `/import-csv`, `/mark-batch`).
  Hoy la web la anuncia como función de Pro. **No lo es.**
- Balance General (`/api/balance`)
- Flujo de caja (`/api/cashflow`)
- Estadísticas del dashboard, alertas y vencimientos

---

## Trial

- **14 días** al registrarse, con todo salvo el panel multiempresa (1 empresa, 3 usuarios,
  sin límites de volumen).
- Al acabar **no se corta el acceso: se cae a Free** con sus límites.
- Si alguien paga durante el trial, manda el plan pagado desde ese momento.
- Red de seguridad en el código: si `trial_ends_at` quedó vacío, se calcula desde
  `created_at`. Existe porque hubo caminos de registro que no lo guardaban.

---

## Discrepancias con la web — corregidas el 16-ago-2026

1. **"Reconciliación bancaria" figuraba como función de Pro** sin estar cerrada en el
   código. Se **quitó de la lista de Pro**, no se cerró por plan: cerrarla habría quitado
   a los usuarios Free y Básico actuales una función que ya usan, y eso es una regresión
   para clientes reales. Si algún día se quiere cerrar, es decisión de producto y toca
   avisar antes a quien la esté usando.
2. **Pro decía "Todos los reportes DGII"** frente al "606, 607, 608" de Básico, como si
   trajera más. Sustituido por el diferenciador real: Estado de Resultados, cierres y
   exportar a CSV.
3. **Básico no avisaba de que no lleva Estado de Resultados ni exportaciones.** Ahora
   aparece explícito en su lista, marcado como no incluido.
4. **Free no mencionaba que genera 606/607/608.** Añadido.

`scripts/verificar-precios.py` prohíbe ya las cadenas "Todos los reportes DGII" y
"Reconciliación bancaria" para que no vuelvan a colarse.
