# Pitch · X Ray · Embat (HackSpain 2026)

5 min (inferido, ambigüedad 6) [CONFIRMAR: duración] · Estructura: por defecto (el análisis no da una) · Presenta: C y B (demo) · Antes de empezar: portátil de B, URL pública abierta, `uv run arranca.py` arrancado como respaldo y vídeo de la ficha a mano.

## Guion
| Tiempo | Bloque | Criterio que cubre | Quién habla | Qué se dice | Qué se ve en pantalla |
|---|---|---|---|---|---|
| 0:00–0:40 | Problema y para quién | Si vale algo (1/3): comprador | C | Embat ya tiene el rastro de banco, facturas y deuda de sus clientes; este módulo le dice a su CFO dónde está, hacia dónde va y qué hacer. | Inicio de la web con acceso en dos clics a las dos empresas |
| 0:40–1:40 | Demo: empresa que mejora | Si acierta (1/3): trayectoria, dos caras · Si vale algo (1/3): producto, explicación | B | Sube de [CIFRA: score inicial] a [CIFRA: score final]; aquí está qué lo movió y qué le proponemos a su CFO. | Ficha: score, curva de 24 meses, flecha, desglose caja/cobros/deuda y acciones con cifra |
| 1:40–2:40 | Demo: empresa que cae con buen nivel | Si acierta (1/3): dos caras · Si vale algo (1/3): explicación, artesanía | B | Nivel aún alto, pero el mismo cálculo marca la caída: [CIFRA: qué la movió, en puntos de score] y la acción concreta que toca. | Ficha de la segunda empresa con flecha a la baja y acción destacada |
| 2:40–3:40 | Cómo funciona y por qué así | Si llega a tiempo (1/3): estabilidad · Si acierta (1/3): generalización | C | Tres señales mensuales y un score suavizado en [CIFRA: meses de suavizado]: un bache de un mes no cambia la tendencia. Modelo sencillo, explicable. | Diapositiva: señales → score suavizado → reglas de acción; [SI DA TIEMPO] curva de una empresa con bache |
| 3:40–4:30 | Quién paga | Si vale algo (1/3): comprador, producto | C | Embat, «el comprador más obvio», lo ofrece como módulo; cada acción cita una cifra de esa empresa, nada genérico: no es un dashboard. | Diapositiva del comprador junto a las acciones de la ficha |
| 4:30–5:00 | Cierre | Los tres bloques | C | Un modelo sencillo con un producto claro encima: score, trayectoria, explicación y acción, abierto por URL ahora mismo. | URL de la demo en grande |

«Si llega a tiempo» queda flojo: la anticipación medida y el monitor que avisa (bonus) no tienen bloque porque el backtest y las alertas están fuera de alcance.

## Si falla la demo
- La URL no abre: demo en local en el portátil de B con `uv run arranca.py` (repliegue del hito de sáb 16:00).
- El motor falla también en local: vídeo grabado de las dos fichas, narrado igual.
- Una empresa da error: se salta a la otra desde el inicio y se cuenta la primera con el vídeo.
- Sin proyector o sin red: el vídeo en el portátil de C.

## Preguntas probables del jurado
| Pregunta | Quién responde | Esqueleto de la respuesta |
|---|---|---|
| ¿Cómo sabéis que el score acierta si no hay etiqueta? | A | No lo llamamos «acertado»: no hay etiqueta (ambigüedad 2). [SI DA TIEMPO] Estabilidad medida en empresas apartadas: [CIFRA: estabilidad en empresas apartadas]. |
| ¿Cuántos meses antes detecta el cambio? | A | No lo hemos medido: el backtest quedó fuera de alcance. Enseñamos la tendencia; medirlo es el siguiente paso. |
| ¿Cómo distinguís un bache de un deterioro? | A | El score se suaviza en [CIFRA: meses de suavizado] y nunca sale solo de la caja del último mes; un bache aislado no gira la flecha. |
| ¿No es solo un dashboard con un número? | C | Cada acción sale de una regla sobre los datos de esa empresa y cita su cifra, por ejemplo [CIFRA: días que se alargan los cobros]. |
| ¿Por qué Embat y por qué pagaría? | C | El enunciado la llama «el comprador más obvio»: ya tiene los datos. Precio y disposición a pagar no están validados. |
| ¿Grupos y monedas? | A | Una ficha por `company_id` y nunca sumamos monedas; cada cifra lleva la suya. Son supuestos pendientes de confirmar (ambigüedades 3 y 8). |

## Cifras que hay que medir
| Hueco | Cómo obtenerla | Dueño | Antes de qué hito |
|---|---|---|---|
| [CIFRA: score inicial] / [CIFRA: score final] | Ficha del motor de la empresa que mejora elegida | C | Sáb 14:00 (elegir empresas) |
| [CIFRA: qué la movió, en puntos de score] | Desglose del motor de la empresa que cae | C | Sáb 14:00 (elegir empresas) |
| [CIFRA: días que se alargan los cobros] | Regla de días de cobro sobre la empresa de la demo | A | Sáb 10:30 (demo mínima) |
| [CIFRA: meses de suavizado] | Parámetro del score suavizado en `motor/` | A | Sáb 03:00 (score) |
| [CIFRA: estabilidad en empresas apartadas] | Solo si Embat pide validación: cambios de tendencia en empresas apartadas | A | Sáb 22:00 (robustez) |
