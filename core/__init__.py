"""Core package cho SPA web app — độc lập hoàn toàn với giao diện Streamlit.

Gồm:
    loader      — đọc file Excel 4 sheet -> (S, P, E, ws, wp, c, G) + metadata
    bounds      — công thức cận trên UB1..UB4 (theo bài báo)
    solver      — dựng & giải 4 mô hình MILP bằng CPLEX (docplex)
    visualizer  — vẽ đồ thị hai phía (input / lời giải)
"""

from .loader import load_instance_from_excel, Instance, SpaValidationError
from .bounds import compute_ub1, compute_ub2, compute_ub3, compute_ub4, compute_ub
from .solver import solve_spa, format_duration, MODEL_NAMES
from .visualizer import visualize_spa_instance

__all__ = [
    "load_instance_from_excel", "Instance", "SpaValidationError",
    "compute_ub1", "compute_ub2", "compute_ub3", "compute_ub4", "compute_ub",
    "solve_spa", "format_duration", "MODEL_NAMES",
    "visualize_spa_instance",
]
