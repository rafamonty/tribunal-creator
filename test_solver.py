import pytest
import pandas as pd
from utils import standardize_columns, get_category_ranks, DEFAULT_CATEGORY_ORDER
from solver import solve_tribunals

def test_standardize_columns():
    df_raw = pd.DataFrame({
        "Apellidos y Nombre": ["Pérez, Juan", "Gómez, Ana"],
        "Categoría": ["CU", "TU"],
        "Antigüedad": [10, 5],
        "MaxTribunales": [3, 2]
    })
    df_clean = standardize_columns(df_raw)
    assert len(df_clean) == 2
    assert "Apellidos y Nombre" in df_clean.columns

def test_solver_basic():
    df_raw = pd.DataFrame({
        "Apellidos y Nombre": [
            "Pérez, Juan", "Gómez, Ana", "López, Pedro", "Sánchez, María"
        ],
        "Categoría": [
            "Catedrático / Catedrática (CU)",
            "Profesor/a Titular (TU)",
            "Profesor/a Ayudante Doctor/a (PAD)",
            "Profesor/a Asociado/a (PA)"
        ],
        "Antigüedad": [15, 10, 5, 2],
        "MaxTribunales": [2, 2, 2, 2]
    })
    df_clean = standardize_columns(df_raw)
    cat_ranks = get_category_ranks(df_clean["Categoría"].unique(), DEFAULT_CATEGORY_ORDER)
    
    # Solve for 1 tribunal (3 members)
    tribunals_df, summary_df, status = solve_tribunals(df_clean, num_tribunals=1, category_rank_map=cat_ranks)
    
    assert status == "Optimal"
    assert len(tribunals_df) == 1
    assert "Presidente" in tribunals_df.columns
    assert "Secretario" in tribunals_df.columns
    assert "Vocal" in tribunals_df.columns
    
    # Verify Presidente is the one with highest category (Pérez, Juan)
    row = tribunals_df.iloc[0]
    assert row["Presidente"] == "Pérez, Juan"
    assert row["Secretario"] in ["López, Pedro", "Sánchez, María"]

def test_seniority_tiebreak():
    # Same category, different antiguedad
    df_raw = pd.DataFrame({
        "Apellidos y Nombre": [
            "Prof A (Alta Antiguedad)", "Prof B (Baja Antiguedad)", "Prof C (Media Antiguedad)"
        ],
        "Categoría": ["TU", "TU", "TU"],
        "Antigüedad": [20, 2, 10],
        "MaxTribunales": [2, 2, 2]
    })
    df_clean = standardize_columns(df_raw)
    cat_ranks = get_category_ranks(df_clean["Categoría"].unique())
    
    tribunals_df, summary_df, status = solve_tribunals(df_clean, num_tribunals=1, category_rank_map=cat_ranks)
    
    row = tribunals_df.iloc[0]
    # Highest seniority -> Presidente
    assert row["Presidente"] == "Prof A (Alta Antiguedad)"
    # Middle seniority -> Vocal
    assert row["Vocal"] == "Prof C (Media Antiguedad)"
    # Lowest seniority -> Secretario
    assert row["Secretario"] == "Prof B (Baja Antiguedad)"

def test_insufficient_capacity_error():
    df_raw = pd.DataFrame({
        "Apellidos y Nombre": ["A", "B", "C"],
        "Categoría": ["TU", "TU", "TU"],
        "Antigüedad": [5, 5, 5],
        "MaxTribunales": [1, 1, 1]  # Total cap = 3
    })
    df_clean = standardize_columns(df_raw)
    cat_ranks = get_category_ranks(df_clean["Categoría"].unique())
    
    # Asking for 2 tribunals (requires 6 slots, but capacity is 3)
    with pytest.raises(ValueError, match="Capacidad insuficiente"):
        solve_tribunals(df_clean, num_tribunals=2, category_rank_map=cat_ranks)
