# Arquitectura Fase 1 — Panamerican Reportes Dinámicos

**Estado:** propuesta técnica para conversación post-sesión con Mariana. NO implementar hasta que Fase 0 esté validada con la cliente.

## Decisiones tomadas (con criterio técnico, no requieren aprobación de Mariana)

| Componente | Elección | Por qué |
|---|---|---|
| Frontend | Lovable (React + Tailwind) | Stack estándar de Boostech, velocidad de desarrollo, percepción de valor alta con la cliente |
| Backend de transformación | Python + FastAPI | El parsing sucio de Eximware es 10× más robusto en Python con pandas que en TypeScript. Reusable para futuros clientes |
| Base de datos | Postgres (no Supabase cloud) | Control total sobre los datos sensibles de trading de la cliente |
| Hosting DB + backend | VPS dedicado Boostech (Hetzner o DigitalOcean) | Política de "infra controlada" que pidió el socio. Costo ≈ US$ 15–25/mes |
| Auth | Lucia Auth o Auth.js self-hosted | Evita depender de servicios externos para autenticar |
| Histórico de cargas | Cada upload = snapshot inmutable con timestamp | Permite comparar períodos sin reprocesar |
| Plantillas de reportes | Guardadas en DB por usuario, con estado compartido opcional | Los "reportes recurrentes" que Mariana defina en la sesión quedan a 1 clic |

## Diagrama conceptual

```
┌────────────────┐     sube 4-6 XLSX     ┌──────────────────┐
│   Lovable UI   │ ─────────────────────▶│  FastAPI Python  │
│ (Mariana + eq.) │                       │  (parsing motor) │
└───────┬────────┘                       └─────────┬────────┘
        │ JSON (reporte + metadata)               │
        │                                         ▼
        │                                 ┌──────────────┐
        │                                 │  Postgres    │
        │   consulta plantillas           │  · snapshots │
        └─────────────────────────────────▶  · plantillas│
                                          │  · usuarios  │
                                          └──────────────┘
```

## Modelo de datos (resumen)

```
organizations (Panamerican, futuro: otros clientes)
  id, name, config_json

users
  id, org_id, email, role (viewer/editor/admin)

snapshots
  id, org_id, uploaded_by, uploaded_at
  files_metadata (nombres, tamaños, hash)
  processing_status (ok / warnings / failed)
  validation_report (json con diffs sospechosos)

rows  (tabla grande, particionada por snapshot_id)
  snapshot_id, ref_#, company, p_s, counter_party, allocation,
  alloc_party, alloc_ref, bl_date, etd, origin, grade, quantity,
  price_status, final_price, fix, ... (todas las cols del reporte final)

saved_reports (las "plantillas" de Mariana)
  id, org_id, created_by, name, description
  columns_to_show (json array)
  filters (json)
  group_by, chart_config
  is_shared (bool)
```

## Endpoints principales (FastAPI)

```
POST   /api/snapshots           → sube 4-6 XLSX, procesa, guarda snapshot + rows
GET    /api/snapshots            → lista snapshots (con paginación)
GET    /api/snapshots/{id}/rows  → devuelve rows del snapshot con filtros en query params
GET    /api/snapshots/{id}/diff/{other_id} → compara dos snapshots
GET    /api/reports              → lista plantillas guardadas
POST   /api/reports              → guarda plantilla
GET    /api/reports/{id}/run     → corre plantilla contra último snapshot (o uno específico)
POST   /api/auth/login           → auth simple
```

## Sprint de entrega (2-3 semanas)

**Sprint 1 — semana 1: backend**
- Setup VPS + Postgres + dominio
- Refactor motor Python actual a FastAPI con endpoints
- Auth básica
- Modelo de datos y migraciones
- Subida y persistencia de snapshots
- Endpoint de query con filtros

**Sprint 2 — semana 2: frontend**
- Lovable: login, upload, dashboard
- Tabla con column selector (reusar UX de la demo)
- Filtros dinámicos conectados al backend
- Gráficos (Recharts)
- Guardar/cargar plantillas

**Sprint 3 — semana 3: pulido + handover**
- Comparación entre snapshots
- Export a Excel/PDF
- Training con Mariana (1 sesión)
- Documentación de usuario
- Monitoring básico (Sentry o logs)

## Costos recurrentes estimados

| Item | Costo mensual |
|---|---|
| VPS (Hetzner CX22) | US$ 5 |
| Dominio + SSL | US$ 1 |
| Backups automáticos | US$ 3 |
| Monitoring (Sentry free tier) | US$ 0 |
| **Total infra** | **≈ US$ 9/mes** |

A facturar a Panamerican como parte del servicio mensual o one-off hosting.

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Eximware cambia formato de export | Media | Medio | Motor basado en nombres de columna, no posiciones. Fácil de ajustar |
| Cliente quiere más empresas (3a+) | Alta | Bajo | Motor ya soporta N empresas sin cambios |
| Mariana pide reporte que requiere joins adicionales | Alta | Bajo | Arquitectura de plantillas permite agregar lógica sin tocar UI |
| Volumen de snapshots crece mucho | Baja | Medio | Particionar tabla `rows` por snapshot. Purgar snapshots viejos a los 12 meses (configurable) |
| Cliente pide acceso desde móvil | Media | Bajo | Lovable genera responsive por default |
| Pérdida de datos por crash del VPS | Baja | Alto | Backups diarios automáticos + replica en segundo VPS barato |

## Qué NO está en alcance de Fase 1

- Integración con Eximware (no tiene API — confirmado por el socio)
- OCR de reportes en PDF (no aplica, Eximware exporta XLSX)
- Roles complejos con permisos por columna
- Notificaciones push / email automáticas
- Mobile app nativa
- Multi-idioma (todo en español)

Esos van a Fase 2 o más adelante, según demanda real.
