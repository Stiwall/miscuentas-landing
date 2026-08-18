# MisCuentas — contrato de medición del funnel

**Objetivo:** dejar definido qué eventos debe medir la landing antes de conectar una herramienta de analítica. Este archivo NO afirma que los eventos ya estén siendo recolectados.

## Funnel principal

1. `landing_view` — visita a una landing.
2. `cta_register_click` — clic hacia registro.
3. `registration_completed` — cuenta creada (debe salir de la app, no de la landing).
4. `company_created` — primera empresa creada.
5. `first_invoice_created` — primera factura.
6. `activation_reached` — usuario alcanzó el criterio de activación que definamos.
7. `checkout_started` — inicio de compra.
8. `subscription_started` — primer pago confirmado.

## Segmentos que deben acompañar el evento

- `source_page`: home / contadores / seguridad / migracion / ecf / blog.
- `cta_location`: hero / pricing / footer / inline.
- `plan_intent`: free / basico / pro / unknown.
- `utm_source`, `utm_medium`, `utm_campaign` cuando existan.

## Regla

No calculamos conversiones desde clics de la landing únicamente. El embudo real termina en la aplicación y en el cobro; por tanto, registro, activación y pago tienen que instrumentarse en `Miscuentas-Contable-App`.

## Siguiente implementación

Cuando vuelva el acceso al repo de la aplicación, localizar: registro, creación de empresa, creación de factura y confirmación del checkout. Después conectar esos eventos con la misma identidad/ID anónimo para poder calcular visita → registro → activación → pago.
