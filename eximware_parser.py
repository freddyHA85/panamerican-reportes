"""
Motor de limpieza y transformación de reportes Eximware para Panamerican Coffee Trade.

Convierte los raw exports sucios (Allocation + Position por empresa) en un
DataFrame consolidado estilo "Reporte Final", listo para filtrado dinámico.

Raw structure de Eximware (ambos tipos):
- Filas 1-5: metadata (titulo, fecha de corte, filtros, sort by)
- Fila 6: headers reales
- Fila 7+: datos, con col A vacía (subtotales) y filas en blanco intercaladas
"""

from __future__ import annotations

import io
from typing import Iterable

import pandas as pd


# ---- Lectura raw ------------------------------------------------------------

def _read_raw(source, header_row: int = 6) -> pd.DataFrame:
    """Lee un xlsx crudo de Eximware, salta la metadata y limpia col A vacía."""
    # header_row en 1-index; pd.read_excel usa 0-index para header
    df = pd.read_excel(source, header=header_row - 1, dtype=object)
    # La col A siempre está vacía (subtotales), la descarto siempre
    first_col = df.columns[0]
    if pd.isna(first_col) or str(first_col).strip() == "" or str(first_col).startswith("Unnamed"):
        df = df.drop(columns=[first_col])
    # Quitar columnas totalmente vacías (Unnamed que no aportan)
    unnamed_empty = [
        c for c in df.columns
        if str(c).startswith("Unnamed") and df[c].isna().all()
    ]
    df = df.drop(columns=unnamed_empty)
    return df


def _strip_subtotals(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """Elimina filas en blanco/subtotales filtrando por la presencia de key_col."""
    return df[df[key_col].notna() & (df[key_col].astype(str).str.strip() != "")].copy()


# ---- Allocation -------------------------------------------------------------

ALLOCATION_KEY = "Reference #/ Shipment #"
_ALLOC_DETAIL_COLS = ["Allocated to", "Ctrt Allocated Quantity"]


def _expand_allocation_subitems(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Expande las sub-filas del Allocation para que cada vínculo P↔S sea una fila.

    Eximware emite sub-filas cuando un contrato tiene múltiples allocations:
    - Fila principal: Reference # completo + datos de columnas B-Q + primer vínculo en R+
    - Sub-filas:      Reference # = NaN, columnas B-Q en blanco, datos del vínculo en R+

    Esta función:
    1. Elimina filas completamente vacías (separadores de sección).
    2. Propaga los valores de la fila padre (columnas B-Q) a las sub-filas,
       de modo que cada sub-fila queda con Reference # y Counter Party correctos.
    3. Preserva los datos propios de cada sub-fila (Allocated to, Ctrt Allocated Quantity, etc.)

    Resultado: una fila por vínculo P↔S, lista para hacer el join 1:N con Positions.
    """
    # Paso 1 — Eliminar filas sin ningún dato relevante (separadores puros)
    def _has_data(row: pd.Series) -> bool:
        for col in [ALLOCATION_KEY] + _ALLOC_DETAIL_COLS:
            if col in row.index:
                v = row[col]
                if pd.notna(v) and str(v).strip() not in ("", "nan"):
                    return True
        return False

    df = df_raw[df_raw.apply(_has_data, axis=1)].copy().reset_index(drop=True)

    # Paso 2 — Identificar las columnas "padre" (B-Q): todas las anteriores a "Allocated to"
    # Estas son las que están en blanco en las sub-filas y deben heredarse del padre.
    if "Allocated to" in df.columns:
        alloc_to_idx = list(df.columns).index("Allocated to")
        parent_cols = list(df.columns[:alloc_to_idx])  # Incluye Reference #
    else:
        parent_cols = [ALLOCATION_KEY]

    # Paso 3 — Forward-fill: propagar campos del padre a sub-filas
    # Solo en columnas B-Q (parent_cols). Los campos R+ (Allocated to, Ctrt Qty, etc.)
    # ya tienen datos propios de la sub-fila y no deben tocarse.
    # EXCEPCIÓN: BL Date y Requested Date NO se propagan — cada sub-fila debe
    # conservar su propio valor (NaN si no tiene fecha asignada en Eximware).
    # Propagar estas fechas causaría que sub-filas sin embarque hereden la fecha
    # del padre, generando sobre-asignación de BL Date en el reporte final.
    _date_no_ffill = {"BL Date", "Requested Date"}
    ffill_cols = [c for c in parent_cols if c not in _date_no_ffill]
    # dtype=object ya garantizado por _read_raw — no hay downcast, ffill directo
    df[ffill_cols] = df[ffill_cols].ffill()

    return df.reset_index(drop=True)


def load_allocation(source, company: str | None = None) -> pd.DataFrame:
    """Carga un raw Allocation de una empresa, preservando sub-filas de allocation múltiple."""
    df = _read_raw(source)
    df = _expand_allocation_subitems(df)
    # Normalizar llave: quitar espacios (paso 5 del docx)
    df[ALLOCATION_KEY] = df[ALLOCATION_KEY].astype(str).str.strip()
    if company:
        df.insert(0, "Company", company)
    return df.reset_index(drop=True)


def unify_allocations(sources: Iterable[tuple[object, str]]) -> pd.DataFrame:
    """Une varios Allocations (uno por empresa). sources: [(file, company), ...]"""
    parts = [load_allocation(src, company) for src, company in sources]
    return pd.concat(parts, ignore_index=True)


# ---- Position ---------------------------------------------------------------

POSITION_KEY = "Ref #"


def load_position(source, company: str | None = None) -> pd.DataFrame:
    df = _read_raw(source)
    # Las Positions a veces tienen 'Ref #' con espacios raros
    df.columns = [str(c).strip() if c is not None else c for c in df.columns]
    # La columna "Price Unit" aparece duplicada en el raw (Q y T). Renombrar la 2da
    cols = list(df.columns)
    seen: dict[str, int] = {}
    new_cols: list[str] = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            new_cols.append(f"{c} ({seen[c]})")
        else:
            seen[c] = 0
            new_cols.append(c)
    df.columns = new_cols
    df = _strip_subtotals(df, POSITION_KEY)
    df[POSITION_KEY] = df[POSITION_KEY].astype(str).str.strip()
    # Eliminar filas con "Washout" (paso 13 del docx)
    mask_washout = df.astype(str).apply(
        lambda row: row.str.contains("Washout", case=False, na=False).any(), axis=1
    )
    df = df[~mask_washout]
    if company:
        df.insert(0, "Company", company)
    return df.reset_index(drop=True)


def unify_positions(sources: Iterable[tuple[object, str]]) -> pd.DataFrame:
    parts = [load_position(src, company) for src, company in sources]
    return pd.concat(parts, ignore_index=True)


# ---- Enriquecimiento --------------------------------------------------------

def compute_price_status(row: pd.Series) -> str:
    """Regla del docx:
    - Fixed (col N, luego renombrada a Final Price) blank  -> PTBF
    - Fixed no blank + Price Diff (K, luego Price Diff)    -> Fixed / Outright
      - Price Diff blank -> Outright
      - Price Diff present -> Fixed
    """
    fixed_val = row.get("Fixed")
    price_diff = row.get("Price Diff")
    if pd.isna(fixed_val) or str(fixed_val).strip() == "":
        return "PTBF"
    if pd.isna(price_diff) or str(price_diff).strip() == "":
        return "Outright"
    return "Fixed"


def _to_num(x):
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return None
        return float(str(x).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def build_reporte_final(
    positions: pd.DataFrame, allocations: pd.DataFrame
) -> pd.DataFrame:
    """Reproduce la lógica del Reporte Final a partir de Positions unidas y Allocations unidas."""
    df = positions.copy()

    # Price Status
    df["Price Status"] = df.apply(compute_price_status, axis=1)

    # Renombrar 'Fixed' -> 'Final Price'
    if "Fixed" in df.columns:
        df = df.rename(columns={"Fixed": "Final Price"})

    # Fix = Final Price - Price Diff (solo para Fixed)
    def _fix(row):
        if row["Price Status"] != "Fixed":
            return None
        fp = _to_num(row.get("Final Price"))
        pd_ = _to_num(row.get("Price Diff"))
        if fp is None or pd_ is None:
            return None
        return fp - pd_

    df["Fix"] = df.apply(_fix, axis=1)

    # Join direccional con Allocation según tipo P/S (derivado empíricamente
    # comparando contra Reporte Final de Mariana):
    #
    # Para Purchase (P): la Position es una compra. Busco en Allocation.Allocated_to
    # para saber a qué Shipment (S) se mandó. Del lado de la Allocation traigo:
    #   - Allocation  = Reference#/Shipment#  (el S### que surtió)
    #   - Alloc. Party = Counter Party         (cliente que recibió el shipment)
    #   - Alloc. Ref  = CP Ref #               (referencia del cliente)
    #   - BL / ETD    = BL Date / Requested Date
    #
    # Para Sale (S): la Position es una venta. Busco en Allocation.Reference#/Shipment#
    # para encontrar la Allocation espejo. Del lado de esa Allocation traigo:
    #   - Allocation  = Allocated to           (el P### que surte la venta)
    #   - Alloc. Party = Allocated Counterparty (productor de quien se compró)
    #   - Alloc. Ref  = Allocated CP REF
    #   - BL / ETD    = BL Date / Requested Date
    alloc = allocations.copy()
    alloc["_alloc_key_p"] = alloc["Allocated to"].astype(str).str.replace(r"\s+", "", regex=True)
    alloc["_alloc_key_s"] = alloc["Reference #/ Shipment #"].astype(str).str.replace(r"\s+", "", regex=True)

    df["_key"] = df[POSITION_KEY].astype(str).str.replace(r"\s+", "", regex=True)
    df["_ps"] = df["_key"].str[0]

    # Para P: el Counter Party de la Allocation a veces trae un sufijo "/ P#####"
    # que es el Internal Ref del contrato. Mariana lo extrae como "Alloc. Ref".
    alloc = alloc.copy()
    def _split_cp(raw):
        if pd.isna(raw):
            return (None, None)
        s = str(raw)
        if "/" in s:
            a, b = s.split("/", 1)
            return (a.strip(), b.strip())
        return (s.strip(), None)
    cp_split = alloc["Counter Party"].apply(_split_cp)
    alloc["_cp_clean"] = cp_split.apply(lambda t: t[0])
    alloc["_cp_internal_ref"] = cp_split.apply(lambda t: t[1])

    cols_p = {
        "Reference #/ Shipment #": "Allocation",
        "_cp_clean": "Alloc. Party",
        "_cp_internal_ref": "Alloc. Ref",
        "BL Date": "BL Date",
        "Requested Date": "ETD",
        "Ctrt Allocated Quantity": "_alloc_qty",  # cantidad por vínculo (P→S parcial)
    }
    alloc_p = (
        alloc[["_alloc_key_p"] + [k for k in cols_p.keys() if k in alloc.columns]]
        .rename(columns={"_alloc_key_p": "_key", **cols_p})
    )
    alloc_p = alloc_p[alloc_p["_key"].notna() & (alloc_p["_key"] != "") & (alloc_p["_key"] != "nan")]
    # SIN drop_duplicates: una P puede estar asociada a múltiples S (lógica bidireccional)

    cols_s = {
        "Allocated to": "Allocation",
        "Allocated Counterparty": "Alloc. Party",
        "Allocated CP REF": "Alloc. Ref",
        "BL Date": "BL Date",
        "Requested Date": "ETD",
        "Ctrt Allocated Quantity": "_alloc_qty",  # cantidad por vínculo (S←P parcial)
    }
    alloc_s = (
        alloc[["_alloc_key_s"] + [k for k in cols_s.keys() if k in alloc.columns]]
        .rename(columns={"_alloc_key_s": "_key", **cols_s})
    )
    alloc_s = alloc_s[alloc_s["_key"].notna() & (alloc_s["_key"] != "") & (alloc_s["_key"] != "nan")]
    # SIN drop_duplicates: una S puede provenir de múltiples P (lógica bidireccional)

    purchases = df[df["_ps"] == "P"].merge(alloc_p, on="_key", how="left")
    sales = df[df["_ps"] == "S"].merge(alloc_s, on="_key", how="left")
    others = df[~df["_ps"].isin(["P", "S"])].copy()
    for c in ["Allocation", "Alloc. Party", "Alloc. Ref", "BL Date", "ETD", "_alloc_qty"]:
        if c not in others.columns:
            others[c] = None
    df = pd.concat([purchases, sales, others], ignore_index=True)
    df["P/S"] = df["_ps"]

    # Cuando hay múltiples allocations por contrato, reemplazar Quantity
    # con la cantidad parcial por vínculo (Ctrt Allocated Quantity del Allocation).
    # Para vínculos 1:1, _alloc_qty == Quantity, así que el reemplazo es inocuo.
    # Para contratos sin allocation, _alloc_qty es NaN → se conserva Quantity original.
    if "_alloc_qty" in df.columns:
        df["_alloc_qty"] = pd.to_numeric(df["_alloc_qty"], errors="coerce")
        df["Quantity"] = df["_alloc_qty"].where(df["_alloc_qty"].notna(), df["Quantity"])
        df = df.drop(columns=["_alloc_qty"])

    df = df.drop(columns=["_key", "_ps"])

    # Normalizar Alloc. Party: evitar strings basura de NaN
    if "Alloc. Party" in df.columns:
        df["Alloc. Party"] = df["Alloc. Party"].replace(
            {"nan": None, "None": None, "": None}
        )

    # Reorden de columnas como Reporte Final
    preferred_order = [
        "Company",
        POSITION_KEY,            # Ref#
        "P/S",
        "Counter Party",
        "CP Ref #",
        "Allocation",
        "Alloc. Party",
        "Alloc. Ref",
        "BL Date",
        "ETD",
        "Origin",
        "Grade",
        "Product Class",
        "Addit Spec",
        "Quantity",
        "UOM",
        "Price Basis",
        "Price Diff",
        "Price Unit",
        "Contract Month",
        "Final Price",
        "Fix",
        "Price Status",
        "Unallocated Qty",
        "Period start",
        "Period end",
        "Position",
        "Price to be fixed at",
        "Account Representative",
    ]
    existing = [c for c in preferred_order if c in df.columns]
    others = [c for c in df.columns if c not in existing]
    df = df[existing + others]

    return df.reset_index(drop=True)


# ---- Orquestador ------------------------------------------------------------

def process_all(
    allocation_files: list[tuple[object, str]],
    position_files: list[tuple[object, str]],
) -> dict[str, pd.DataFrame]:
    """Pipeline completo. Devuelve dict con las tablas intermedias + final."""
    allocations = unify_allocations(allocation_files)
    positions = unify_positions(position_files)
    final = build_reporte_final(positions, allocations)
    return {
        "allocations": allocations,
        "positions": positions,
        "reporte_final": final,
    }
