# Panamerican Coffee Trade — Reportes Dinámicos (Fase 0 · Demo)

Prototipo en Streamlit para validar UX con Mariana antes de construir la versión productiva en Lovable + backend Python.

**Objetivo de esta fase:** alinear con la cliente qué reportes quiere ver, qué filtros, qué columnas y qué gráficos — con una herramienta que *ya funciona punta a punta* sobre los datos reales que ella envió el 14-abr-2026.

## Cómo correrlo

```bash
# 1. Instalar dependencias (una sola vez)
pip install pandas openpyxl streamlit

# 2. Parado en esta carpeta, copiar los 4 archivos raw de Eximware:
#    - Allocation LLC.xlsx
#    - Allocation PCT.xlsx
#    - Position LLC.xlsx
#    - Position PCT.xlsx

# 3. Arrancar la demo
streamlit run app.py
```

Se abre en http://localhost:8501. Activar el toggle "Usar datos de demo" en el sidebar si los archivos están en la carpeta. Darle a **Procesar**.

## Qué hace el motor (`eximware_parser.py`)

Replica el proceso manual del docx PROCESO DE REPORTES.docx en 50 líneas de Python:

1. **Lee los crudos sin limpiar** — salta filas 1-5 (metadata), usa fila 6 como header, descarta columna A vacía y filas de subtotales.
2. **Une Allocations** (LLC + PCT + opcionalmente 3ra empresa) y **une Positions** (idem).
3. **Enriquecimiento**:
   - Calcula `Price Status` (PTBF / Outright / Fixed) según la lógica del docx.
   - Renombra `Fixed` → `Final Price`, calcula `Fix` = Final Price − Price Diff.
   - Elimina filas con "Washout".
4. **Join direccional Position ↔ Allocation** (ésta es la parte no-trivial):
   - Para una Purchase (P): busca en `Allocation.Allocated_to` → trae Counter Party del shipment, BL Date, ETD, Allocated Ref interno.
   - Para una Sale (S): busca en `Allocation.Reference#` → trae Allocated Counterparty del lado compra.
5. **Devuelve un DataFrame consolidado** comparable al "Reporte Final" que la cliente arma a mano.

## Validación contra el Reporte Final de Mariana

Comparando las 2.239 filas que Mariana tiene hoy vs. las 2.240 que genera el motor:

| Campo | Match exacto | Rellena gaps de Mariana | Motor vacío | Diferente |
|---|---|---|---|---|
| Price Status | 100% | 0 | 0 | 0 |
| Counter Party | 100% | — | — | — |
| Origin | 100% | — | — | — |
| Quantity | 100% | — | — | — |
| BL Date | 89% | 176 | 32 | 41 |
| Alloc. Party | 82% | 392 | 20 | 1 |
| Allocation | 80% | 392 | 20 | 32 |
| Alloc. Ref | 75% | 319 | 18 | 217 |

**Lectura:** las diferencias con la columna `Alloc. Party / Allocation` están dominadas por "rellena gaps" — casos donde el VLOOKUP manual de Mariana devolvía `#N/A` o vacío (ella lo reconoció en su correo) y el motor sí encuentra el match correcto. Los 217 "diferente" de `Alloc. Ref` son el edge case que hay que confirmar con ella: cuando un Ref tiene múltiples Allocations, el motor toma el primer match, pero ella puede haber priorizado otro criterio en el VLOOKUP.

## Caso demo funcionando

El ejemplo del correo de Mariana ("Ventas pendientes de embarque DEK Nicaragua, solo cantidades") se ejecuta en 3 clics:

1. Filtrar `P/S = S`
2. Filtrar `Counter Party = DEK, DEK Hbg`
3. Filtrar `BL Date = Sin fecha (pendiente)`
4. (Opcional) Filtrar `Origin = Nicaragua`

Resultado (al 14-abr-2026, todos los orígenes de DEK pendientes): **30 líneas, 68.400 unidades**
- Honduras: 47.700
- Perú: 20.100
- Colombia: 600
- *(Nicaragua: 0 en este snapshot — caso a mencionar en la sesión)*

## Qué NO es esto

- No es la herramienta productiva. No tiene auth, ni multi-usuario, ni histórico persistente.
- No corre en la nube — es para correr localmente durante la sesión con Mariana.
- Las plantillas de reportes recurrentes que Mariana mencione en la sesión aún no están implementadas.

## Siguiente paso (Fase 1, post-sesión)

Ver `GUION_SESION_MARIANA.md` para el guión de la reunión y la propuesta de arquitectura Fase 1.
