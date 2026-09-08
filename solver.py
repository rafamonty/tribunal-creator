import numpy as np
import scipy.optimize as opt
import pulp
import pandas as pd
from typing import Dict, List, Tuple

def solve_tribunals(
    df_professors: pd.DataFrame,
    num_tribunals: int,
    category_rank_map: Dict[str, int]
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Solves the tribunal assignment optimization problem using scipy MILP (HiGHS solver)
    in milliseconds, with zero subprocess blocking.
    """
    if num_tribunals <= 0:
        raise ValueError("El número de tribunales debe ser mayor que 0.")
        
    num_professors = len(df_professors)
    if num_professors < 3:
        raise ValueError(f"Se requieren al menos 3 profesores en la plantilla (actualmente hay {num_professors}).")
        
    required_slots = num_tribunals * 3
    total_capacity = df_professors["MaxTribunales"].sum()
    
    if total_capacity < required_slots:
        raise ValueError(
            f"Capacidad insuficiente: Se requieren {required_slots} participaciones en total "
            f"({num_tribunals} tribunales × 3 miembros), pero el máximo disponible entre todos los profesores "
            f"es de {total_capacity}."
        )

    professors = df_professors.to_dict("records")
    M = num_professors
    N = num_tribunals
    
    solution_matrix = None
    status_str = "Optimal"
    
    # Solve with Scipy MILP (In-process, hyper-fast C++ HiGHS solver)
    try:
        c = np.zeros(M * N)
        for i in range(M):
            max_t = max(1, professors[i]["MaxTribunales"])
            for t in range(N):
                c[i * N + t] = (1.0 / max_t) + (((i * 17 + t * 31) % 97) / 1000.0)

        num_constraints = N + M
        A = np.zeros((num_constraints, M * N))

        # 1) N constraints for tribunals: sum_i x_{i,t} == 3
        for t in range(N):
            for i in range(M):
                A[t, i * N + t] = 1.0

        # 2) M constraints for professors: sum_t x_{i,t} <= MaxTribunales_i
        for i in range(M):
            for t in range(N):
                A[N + i, i * N + t] = 1.0

        b_l = np.concatenate([np.full(N, 3.0), np.zeros(M)])
        b_u = np.concatenate([np.full(N, 3.0), np.array([p["MaxTribunales"] for p in professors], dtype=float)])

        bounds = opt.Bounds(0, 1)
        constraints = opt.LinearConstraint(A, b_l, b_u)
        integrality = np.ones(M * N)  # Binary decision variables

        res = opt.milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

        if res.success and res.x is not None:
            x_val = np.round(res.x).reshape((M, N))
            solution_matrix = x_val
            status_str = "Optimal"
        else:
            status_str = f"Scipy Status: {res.message}"
    except Exception as e:
        status_str = f"Scipy Exception: {e}"

    # Fallback to PuLP if scipy didn't solve
    if solution_matrix is None:
        prob = pulp.LpProblem("Tribunal_Assignment", pulp.LpMinimize)
        x = {}
        for i in range(M):
            for t in range(N):
                x[i, t] = pulp.LpVariable(f"x_{i}_{t}", cat=pulp.LpBinary)

        for t in range(N):
            prob += (pulp.lpSum([x[i, t] for i in range(M)]) == 3)

        for i, prof in enumerate(professors):
            prob += (pulp.lpSum([x[i, t] for t in range(N)]) <= prof["MaxTribunales"])

        cost_terms = []
        for i, prof in enumerate(professors):
            max_t = max(1, prof["MaxTribunales"])
            for t in range(N):
                cost_terms.append(x[i, t] * ((1.0 / max_t) + (((i * 17 + t * 31) % 97) / 1000.0)))

        prob += pulp.lpSum(cost_terms)
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=5)
        prob.solve(solver)
        
        status_str = pulp.LpStatus[prob.status]
        solution_matrix = np.zeros((M, N))
        for i in range(M):
            for t in range(N):
                if pulp.value(x[i, t]) and pulp.value(x[i, t]) > 0.5:
                    solution_matrix[i, t] = 1.0

    # Extract assignments per tribunal
    tribunal_results = []
    prof_assignments = {i: [] for i in range(M)}
    
    for t in range(N):
        assigned_indices = [i for i in range(M) if solution_matrix[i, t] > 0.5]
        for idx in assigned_indices:
            prof_assignments[idx].append(t + 1)
            
        assigned_profs = [professors[i] for i in assigned_indices]
        
        # Sort professors for role assignment:
        # Sort key: (Category Rank Descending, Antigüedad Descending, Name Ascending)
        def get_sort_key(p):
            cat_rank = category_rank_map.get(p["Categoría"], 0)
            antig = float(p["Antigüedad"])
            return (cat_rank, antig, p["Apellidos y Nombre"])
            
        sorted_profs = sorted(assigned_profs, key=get_sort_key, reverse=True)
        
        presidente = sorted_profs[0]["Apellidos y Nombre"]
        vocal = sorted_profs[1]["Apellidos y Nombre"]
        secretario = sorted_profs[2]["Apellidos y Nombre"]
        
        tribunal_results.append({
            "ID_TRIBUNAL": f"Tribunal_{t + 1:02d}",
            "Presidente": presidente,
            "Secretario": secretario,
            "Vocal": vocal
        })
        
    tribunals_df = pd.DataFrame(tribunal_results)
    
    # Summary of professor participation & roles
    summary_list = []
    for i, prof in enumerate(professors):
        name = prof["Apellidos y Nombre"]
        assigned_t_list = prof_assignments[i]
        count_assigned = len(assigned_t_list)
        
        pres_count = sum(1 for row in tribunal_results if row["Presidente"] == name)
        voc_count = sum(1 for row in tribunal_results if row["Vocal"] == name)
        sec_count = sum(1 for row in tribunal_results if row["Secretario"] == name)
        
        summary_list.append({
            "Apellidos y Nombre": name,
            "Categoría": prof["Categoría"],
            "Antigüedad": prof["Antigüedad"],
            "MaxTribunales": prof["MaxTribunales"],
            "Tribunales Asignados": count_assigned,
            "Desempeñó Presidente": pres_count,
            "Desempeñó Vocal": voc_count,
            "Desempeñó Secretario": sec_count,
            "Tribunales": ", ".join([f"T{t}" for t in assigned_t_list]) if assigned_t_list else "-"
        })
        
    summary_df = pd.DataFrame(summary_list)
    
    return tribunals_df, summary_df, status_str
