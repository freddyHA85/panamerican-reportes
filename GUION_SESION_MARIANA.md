# Guión sesión con Mariana — Panamerican Reportes Dinámicos

**Duración estimada:** 45–60 min
**Objetivo único de la sesión:** alinear qué reportes quiere ver, con qué filtros, qué columnas y qué gráficos. **No** cerrar requerimientos de auth, histórico ni infra todavía.

---

## Antes de la sesión (checklist propio)

- [ ] Verificar que `streamlit run app.py` arranca en menos de 5 seg
- [ ] Tener abiertos: la demo (localhost:8501), el correo de Mariana, el docx PROCESO DE REPORTES
- [ ] Tener lista una libreta o Notion para anotar en vivo los reportes que ella mencione
- [ ] Llevar preparado un slide/foto del diagrama Fase 1 (Lovable + backend + Supabase) pero NO mostrarlo todavía — reservarlo para cuando ella apruebe el concepto

---

## Arranque (5 min)

Frase de apertura: *"Antes de construir la herramienta final, te quería mostrar algo que ya corre punta a punta sobre los datos que me mandaste. La idea es que validemos juntos la experiencia antes de meter 3 semanas de desarrollo. Si algo no cuadra, lo ajustamos ahora que es barato."*

Mostrar el flujo completo:

1. Sidebar: **Procesar** con datos demo.
2. KPIs arriba: "mirá, 2.240 registros, 951 compras, 1.289 ventas. Esto el sistema hoy te lo da en cero clics."
3. Demo del caso de ella: **DEK pendientes de embarque** → 30 filas, 68.400 unidades. Agrupado por origen en el gráfico.

Expectativa: que ella diga "esto es justo lo que quería" o "sí pero además...".

---

## Preguntas a hacer (12–15 min)

### Reportes recurrentes (prioridad máxima)

> *"En tu correo dijiste 'luego dejamos fijados los de uso recurrente'. Contame cuáles son — los 3-5 que corrés más seguido. Esos los voy a dejar guardados como 'plantillas' en un clic."*

Anotar para cada reporte:
- Nombre
- Columnas a mostrar
- Filtros fijos
- Agrupación y gráfico
- Frecuencia (diario/semanal/mensual)
- Para quién es (ella, Pto de operaciones, dirección)

### Brechas de datos (validación crítica del motor)

> *"En tu Reporte Final actual tenés varias filas con `#N/A` en Alloc. Party. El motor nuevo les llena el dato correcto — quiero que verifiques 5 casos puntuales para confirmar que lo que le ponemos es lo que esperabas."*

Tomar 5 Refs aleatorios donde hay "rellena gap" y revisarlos contigo.

### Casos con múltiples allocations

> *"Hay 217 Refs donde tu Excel marcaba una Allocation diferente a la que el motor elige. Cuando un Ref tiene varios shipments, ¿cuál querés ver? ¿El más reciente? ¿El que tiene mayor cantidad? ¿Todos?"*

### Métricas / cálculos nuevos

> *"Más allá de sumar Quantity, ¿hay otros cálculos que te piden en los reportes? Por ejemplo: cantidad promedio por contrato, días desde el contrato hasta el BL, cumplimiento de entregas, algo así."*

### 3ra empresa

> *"Mencionaste que son 3 empresas pero solo bajaste 2 por el error de Eximware. ¿Cuándo estimás que se resuelve? El motor ya está preparado para la 3ra, solo hay que subirla."*

---

## Decisiones que llevás vos (no preguntar a Mariana, solo informarle)

Basado en tu confirmación previa (el socio decide infra con criterio técnico):

- **Arquitectura Fase 1:** Lovable frontend + Python FastAPI backend en Railway + Postgres self-hosted (VPS propio de Boostech o similar) para persistir histórico.
- **Auth:** Supabase Auth limitado a los 3-4 usuarios que ella designe.
- **Histórico:** cada carga queda versionada automáticamente. Podrán comparar snapshots.
- **Política de datos:** servidor bajo control de Boostech, no cloud público genérico. Le explicás a ella el arreglo y confirmás que le cuadra.

Le mostrás el diagrama Fase 1 solo *después* de validar Fase 0. Si le cuadra la demo, le decís: *"Esto que viste, lo envolvemos en esta arquitectura, le agregamos login, le agregamos histórico y plantillas guardadas. 2-3 semanas."*

---

## Preguntas que Mariana probablemente te hará (y cómo responder)

**¿Cuánto me va a costar?**
→ No improvisar. Decirle que lo cotizás esta semana con alcance claro tras la sesión.

**¿Se puede automatizar la bajada de Eximware?**
→ "No tiene API, entonces no. Pero podríamos ver si hay forma via bot/scraping en fase 3. Por ahora, carga manual — que es lo que vos ya haces hoy."

**¿Puedo usarlo mientras tanto?**
→ "Hoy es una demo local. No la uses en producción todavía. En 2-3 semanas te entrego la versión con auth e histórico."

**¿Qué pasa si Eximware cambia el formato del reporte?**
→ "El motor detecta headers por nombre, no por posición. Si Eximware cambia el nombre de una columna, hago un ajuste de 5 minutos. Si cambia el formato de los raws (ej: quita los subtotales, cambia el header row), hago un ajuste de 30 minutos. Está diseñado para aguantar cambios sin reescribir todo."

---

## Al cierre (5 min)

Resumir en voz alta lo que vas a entregarle y cuándo:

1. Plan detallado de Fase 1 con cotización → **en X días**
2. Lista de las plantillas de reportes que ella definió → **confirmada en el plan**
3. Arquitectura técnica resumida → **una página**
4. Primera entrega de Fase 1 funcionando → **2-3 semanas después de firmado el plan**

Cerrar con: *"Todo lo que viste hoy ya existe en código. El trabajo de Fase 1 es envolverlo con auth, histórico, y tu ambiente."* Eso evita que piense que "todavía no hay nada".

---

## Después de la sesión (punch list)

- [ ] Procesar las notas de la sesión en el vault de Obsidian (carpeta Panamerican)
- [ ] Escribir la cotización Fase 1 con el alcance ajustado
- [ ] Mandar por correo: plantillas definidas + cotización + diagrama + plan de sprint
- [ ] Configurar en Boostech un task recurrente para validar el motor cada vez que ellos descarguen datos nuevos (hasta que Fase 1 esté live)
