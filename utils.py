import pandas as pd
import openpyxl
from io import BytesIO
from typing import Dict, List, Tuple

# Default standard category hierarchy (higher score = higher category)
DEFAULT_CATEGORY_ORDER = [
    "Catedrático / Catedrática (CU)",
    "Profesor/a Titular (TU)",
    "Profesor/a Contratado/a Doctor/a (PCD) / Permanente Laboral",
    "Profesor/a Ayudante Doctor/a (PAD)",
    "Profesor/a Asociado/a (PA)",
    "Otro / Colaborador"
]

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardizes input dataframe column names."""
    col_mapping = {}
    for col in df.columns:
        col_clean = str(col).strip().lower()
        if "apellido" in col_clean or "nombre" in col_clean or "profesor" in col_clean:
            col_mapping[col] = "Apellidos y Nombre"
        elif "categor" in col_clean:
            col_mapping[col] = "Categoría"
        elif "antig" in col_clean or "año" in col_clean or "year" in col_clean:
            col_mapping[col] = "Antigüedad"
        elif "max" in col_clean or "tribunal" in col_clean:
            col_mapping[col] = "MaxTribunales"
    
    df_renamed = df.rename(columns=col_mapping)
    required_cols = ["Apellidos y Nombre", "Categoría", "Antigüedad", "MaxTribunales"]
    missing = [c for c in required_cols if c not in df_renamed.columns]
    if missing:
        raise ValueError(f"Faltan las siguientes columnas requeridas en el Excel: {', '.join(missing)}")
    
    # Clean data types
    df_renamed["Apellidos y Nombre"] = df_renamed["Apellidos y Nombre"].astype(str).str.strip()
    df_renamed["Categoría"] = df_renamed["Categoría"].astype(str).str.strip()
    df_renamed["Antigüedad"] = pd.to_numeric(df_renamed["Antigüedad"], errors="coerce").fillna(0.0)
    df_renamed["MaxTribunales"] = pd.to_numeric(df_renamed["MaxTribunales"], errors="coerce").fillna(0).astype(int)
    
    return df_renamed[required_cols]

def get_category_ranks(categories: List[str], custom_order: List[str] = None) -> Dict[str, int]:
    """
    Returns a dictionary mapping category names to integer ranks.
    Higher rank number means HIGHER category hierarchy.
    """
    if custom_order:
        order_list = custom_order
    else:
        order_list = DEFAULT_CATEGORY_ORDER

    # Map categories in custom order list (top of list = highest rank)
    n = len(order_list)
    rank_map = {}
    for idx, cat in enumerate(order_list):
        rank_map[cat.strip().lower()] = n - idx
    
    # For any categories not explicitly in order_list, assign rank 0 or numeric rank if convertible
    result = {}
    for cat in categories:
        cat_clean = str(cat).strip().lower()
        if cat_clean in rank_map:
            result[cat] = rank_map[cat_clean]
        else:
            # Check if category is numeric
            try:
                result[cat] = int(float(cat))
            except ValueError:
                # Assign default low rank
                result[cat] = 0
    return result

def generate_sample_excel() -> bytes:
    """Generates a sample Excel file for users to download as template."""
    sample_data = [
        {"Apellidos y Nombre": "García Pérez, María", "Categoría": "Catedrático / Catedrática (CU)", "Antigüedad": 15, "MaxTribunales": 4},
        {"Apellidos y Nombre": "López Martínez, Juan", "Categoría": "Catedrático / Catedrática (CU)", "Antigüedad": 12, "MaxTribunales": 3},
        {"Apellidos y Nombre": "Fernández Gómez, Ana", "Categoría": "Profesor/a Titular (TU)", "Antigüedad": 10, "MaxTribunales": 4},
        {"Apellidos y Nombre": "Sánchez Rodríguez, Carlos", "Categoría": "Profesor/a Titular (TU)", "Antigüedad": 8, "MaxTribunales": 3},
        {"Apellidos y Nombre": "González Ruiz, Laura", "Categoría": "Profesor/a Titular (TU)", "Antigüedad": 6, "MaxTribunales": 2},
        {"Apellidos y Nombre": "Romero Díaz, David", "Categoría": "Profesor/a Contratado/a Doctor/a (PCD) / Permanente Laboral", "Antigüedad": 5, "MaxTribunales": 3},
        {"Apellidos y Nombre": "Torres Navarro, Elena", "Categoría": "Profesor/a Contratado/a Doctor/a (PCD) / Permanente Laboral", "Antigüedad": 4, "MaxTribunales": 2},
        {"Apellidos y Nombre": "Navarro Serrano, Javier", "Categoría": "Profesor/a Ayudante Doctor/a (PAD)", "Antigüedad": 3, "MaxTribunales": 3},
        {"Apellidos y Nombre": "Jiménez Castro, Sofía", "Categoría": "Profesor/a Ayudante Doctor/a (PAD)", "Antigüedad": 2, "MaxTribunales": 2},
        {"Apellidos y Nombre": "Ruiz Morales, Pablo", "Categoría": "Profesor/a Asociado/a (PA)", "Antigüedad": 1, "MaxTribunales": 2},
    ]
    df = pd.DataFrame(sample_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Profesores")
    return output.getvalue()

def export_results_to_excel(tribunals_df: pd.DataFrame, professor_summary_df: pd.DataFrame) -> bytes:
    """Exports tribunal assignment and professor summary to Excel bytes."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        tribunals_df.to_excel(writer, index=False, sheet_name="Tribunales")
        professor_summary_df.to_excel(writer, index=False, sheet_name="Resumen Profesores")
        
        # Formatting workbook
        workbook = writer.book
        worksheet_tribunals = writer.sheets["Tribunales"]
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#1F4E78', 'font_color': '#FFFFFF', 'border': 1
        })
        for col_num, value in enumerate(tribunals_df.columns.values):
            worksheet_tribunals.write(0, col_num, value, header_format)
            worksheet_tribunals.set_column(col_num, col_num, 28)
            
        worksheet_prof = writer.sheets["Resumen Profesores"]
        for col_num, value in enumerate(professor_summary_df.columns.values):
            worksheet_prof.write(0, col_num, value, header_format)
            worksheet_prof.set_column(col_num, col_num, 25)
            
    return output.getvalue()
