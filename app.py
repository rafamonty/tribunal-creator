import streamlit as st
import pandas as pd
import importlib
import utils
import solver

# Force module reload to ensure newest solver code is always executed
importlib.reload(utils)
importlib.reload(solver)

st.set_page_config(
    page_title="Generador de Tribunales de Tesis",
    page_icon="🎓",
    layout="wide"
)

# Custom CSS styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        color: #1F4E78;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background-color: #1F4E78;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎓 Asistente para la Generación de Tribunales de Evaluación</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Asignación optimizada de profesores para tribunales de tesis de Máster (3 miembros: Presidente, Secretario y Vocal).</div>', unsafe_allow_html=True)

# Sidebar with Instructions and Template Download
st.sidebar.header("📁 Instrucciones y Plantilla")
st.sidebar.info("""
**Instrucciones de uso:**
1. Suba un archivo Excel con la plantilla de profesores.
2. Ingrese el número de estudiantes / tribunales a evaluar.
3. Ajuste la jerarquía de categorías si fuera necesario.
4. Haga clic en **Generar Tribunales**.
""")

# Download sample template button
sample_xlsx_bytes = utils.generate_sample_excel()
st.sidebar.download_button(
    label="📥 Descargar Excel de Ejemplo / Plantilla",
    data=sample_xlsx_bytes,
    file_name="plantilla_profesores_ejemplo.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Column layout for input section
col_file, col_params = st.columns([3, 2])

with col_file:
    st.subheader("1. Cargar Datos de Profesores")
    uploaded_file = st.file_uploader(
        "Seleccione o arrastre el archivo Excel (.xlsx)",
        type=["xlsx", "xls"]
    )

with col_params:
    st.subheader("2. Parámetros de la Evaluación")
    num_tribunals = st.number_input(
        "Número de tribunales a generar (Nº de alumnos):",
        min_value=1,
        max_value=500,
        value=5,
        step=1
    )

df_prof = None

if uploaded_file is not None:
    try:
        raw_df = pd.read_excel(uploaded_file)
        df_prof = utils.standardize_columns(raw_df)
        st.success(f"✅ Se han cargado **{len(df_prof)}** profesores correctamente desde el archivo.")
    except Exception as e:
        st.error(f"❌ Error al procesar el archivo Excel: {e}")

else:
    st.info("ℹ️ Para probar la herramienta, cargue un archivo o use los datos de ejemplo a continuación.")
    if st.checkbox("Usar datos de plantilla por defecto para demostración"):
        df_sample = pd.read_excel(utils.generate_sample_excel())
        df_prof = utils.standardize_columns(df_sample)

# Category hierarchy ranking section
category_rank_map = {}
if df_prof is not None:
    st.markdown("---")
    st.subheader("3. Vista Previa y Jerarquía de Categorías")
    
    unique_cats = df_prof["Categoría"].unique().tolist()
    
    with st.expander("⚙️ Orden jerárquico de Categorías Profesionales (Mayor a Menor)", expanded=False):
        st.caption("Ajuste el orden jerárquico de mayor a menor categoría. El Presidente se asigna según la categoría superior; en caso de empate, por antigüedad.")
        
        default_order = [c for c in utils.DEFAULT_CATEGORY_ORDER if c in unique_cats]
        remaining = [c for c in unique_cats if c not in default_order]
        current_cat_list = default_order + remaining
        
        ordered_cats = st.multiselect(
            "Orden de categorías (de MAYOR a MENOR rango):",
            options=unique_cats,
            default=current_cat_list
        )
        
        category_rank_map = utils.get_category_ranks(unique_cats, custom_order=ordered_cats)

    # Show preview table of loaded professors
    st.dataframe(df_prof, width=1200, hide_index=True)
    
    # Calculate Capacity metrics
    total_prof = len(df_prof)
    total_cap = df_prof["MaxTribunales"].sum()
    req_slots = num_tribunals * 3
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Profesores en Plantilla", total_prof)
    c2.metric("Tribunales a Generar", num_tribunals)
    c3.metric("Plazas Requeridas (3 × N)", req_slots)
    c4.metric("Capacidad Total Máxima", total_cap, delta=total_cap - req_slots)

    if total_cap < req_slots:
        st.warning(f"⚠️ La capacidad total de la plantilla ({total_cap}) es menor que el número de plazas requeridas ({req_slots}). Debe aumentar 'MaxTribunales' o reducir el número de tribunales.")

    st.markdown("---")
    
    if st.button("🚀 Generar Tribunales", key="btn_generar"):
        with st.spinner("Optimizando asignación de tribunales..."):
            try:
                tribunals_df, summary_df, status = solver.solve_tribunals(
                    df_professors=df_prof,
                    num_tribunals=num_tribunals,
                    category_rank_map=category_rank_map
                )
                
                st.session_state["tribunals_df"] = tribunals_df
                st.session_state["summary_df"] = summary_df
                st.session_state["solved"] = True
                st.toast("¡Tribunales generados con éxito!", icon="🎉")
            except Exception as ex:
                st.error(f"❌ Error al solucionar: {ex}")

# Display Results if Solved
if st.session_state.get("solved", False):
    tribunals_df = st.session_state["tribunals_df"]
    summary_df = st.session_state["summary_df"]
    
    st.header("📋 Resultados de la Asignación")
    
    tab1, tab2 = st.tabs(["🏛️ Lista de Tribunales", "📊 Resumen de Profesores"])
    
    with tab1:
        st.dataframe(tribunals_df, width=1200, hide_index=True)
        
    with tab2:
        st.dataframe(summary_df, width=1200, hide_index=True)
        
    # Excel Download
    excel_result_bytes = utils.export_results_to_excel(tribunals_df, summary_df)
    st.download_button(
        label="📥 Descargar Resultado Completo en Excel (.xlsx)",
        data=excel_result_bytes,
        file_name=f"tribunales_asignados_{num_tribunals}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
