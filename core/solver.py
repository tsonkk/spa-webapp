"""Dựng và giải 4 mô hình MILP bằng CPLEX (docplex).

Giữ đúng cấu trúc mô hình trong bài báo:
    (1) mỗi SV được gán ĐÚNG 1 đề tài đã đăng ký   (đẳng thức)
    (2) sức chứa đề tài không vượt quá c_j
    (3a/3b/3c) ràng buộc nhóm (chỉ MILP4)

Mục tiêu:
    MILP1: max Σ x_ij
    MILP2: max Σ ws_ij · x_ij
    MILP3: max Σ (ws_ij + wp_ij) · x_ij
    MILP4: như MILP3, thêm ràng buộc nhóm

Trả về dict: status, feasible, obj, seconds (giá trị chính xác), solution, conflicts.
Đo thời gian bằng perf_counter QUANH model.solve() (đồng nhất cách đo trong luận văn).
"""

from time import perf_counter

from docplex.mp.model import Model

MODEL_NAMES = {
    1: "MILP1 — Tối đa số SV được phân",
    2: "MILP2 — + Nguyện vọng sinh viên",
    3: "MILP3 — + Quan tâm của giảng viên",
    4: "MILP4 — + Ràng buộc nhóm",
}


def format_duration(seconds):
    """Auto-scale: < 1 ms hiện µs, < 1 s hiện ms, còn lại hiện s."""
    if seconds is None:
        return "—"
    ms = seconds * 1000.0
    if ms < 1.0:
        us = seconds * 1_000_000.0
        return f"{us:.0f} µs" if us >= 10 else f"{us:.1f} µs"
    if ms < 1000.0:
        return f"{ms:.2f} ms"
    return f"{seconds:.2f} s"


def _add_common_constraints(model, x, S, P, E, c):
    for i in S:                                        # (1) gán đúng 1
        model.add_constraint(model.sum(x[e] for e in E if e[0] == i) == 1,
                             ctname=f"c1_assign_{i}")
    for j in P:                                        # (2) sức chứa
        model.add_constraint(model.sum(x[e] for e in E if e[1] == j) <= c[j],
                             ctname=f"c2_cap_{j}")


def _add_group_constraints(model, x, P, E, G):
    for j in P:                                        # (3) ràng buộc nhóm
        for (i1, i2) in G:
            if (i1, j) in E and (i2, j) in E:                       # (3a)
                model.add_constraint(x[(i1, j)] == x[(i2, j)],
                                     ctname=f"c3a_{i1}_{i2}_{j}")
            elif (i1, j) in E and (i2, j) not in E:                 # (3b)
                model.add_constraint(x[(i1, j)] == 0, ctname=f"c3b_{i1}_{j}")
            elif (i1, j) not in E and (i2, j) in E:                 # (3c)
                model.add_constraint(x[(i2, j)] == 0, ctname=f"c3c_{i2}_{j}")


def _build_model(model_id, S, P, E, ws, wp, c, G):
    model = Model(name=f"SPA-M{model_id}")
    x = model.binary_var_dict(E, name="x")

    if model_id == 1:
        model.maximize(model.sum(x[e] for e in E))
    elif model_id == 2:
        model.maximize(model.sum(ws[e] * x[e] for e in E))
    else:  # 3 và 4 cùng mục tiêu
        model.maximize(model.sum((ws[e] + wp[e]) * x[e] for e in E))

    _add_common_constraints(model, x, S, P, E, c)
    if model_id == 4:
        _add_group_constraints(model, x, P, E, G)

    return model, x


def _refine_conflicts(model):
    """Khi vô nghiệm: chỉ ra các ràng buộc xung đột (best-effort)."""
    try:
        from docplex.mp.conflict_refiner import ConflictRefiner
        res = ConflictRefiner().refine_conflict(model)
        msgs = []
        for item in res:
            name = getattr(getattr(item, "element", None), "name", None) or str(item)
            msgs.append(name)
        # loại trùng, giữ thứ tự
        seen, uniq = set(), []
        for m in msgs:
            if m not in seen:
                seen.add(m); uniq.append(m)
        return uniq or ["Không xác định được ràng buộc xung đột cụ thể."]
    except Exception as ex:
        return [f"Không chạy được ConflictRefiner: {ex}"]


def _status_name(model):
    st = model.get_solve_status()
    return getattr(st, "name", str(st))


def solve_spa(model_id, S, P, E, ws, wp, c, G):
    """Giải mô hình MILP{model_id}. Trả về dict kết quả.

    status có thể là: 'optimal'/'feasible' (giải được), 'infeasible' (vô nghiệm),
    'limit_exceeded' (vượt giới hạn CPLEX Community 1000 biến/ràng buộc), 'error'.
    """
    if model_id not in (1, 2, 3, 4):
        raise ValueError("model_id phải là 1, 2, 3 hoặc 4.")

    model, x = _build_model(model_id, S, P, E, ws, wp, c, G)
    n_vars = model.number_of_variables
    n_cons = model.number_of_constraints

    base = {"model_id": model_id, "n_vars": n_vars, "n_cons": n_cons}

    t0 = perf_counter()
    try:
        sol = model.solve()
    except Exception as ex:                       # community edition: giới hạn kích thước
        seconds = perf_counter() - t0
        msg = str(ex)
        low = msg.lower()
        is_limit = ("1016" in msg) or ("limits exceeded" in low) or ("promotional" in low)
        model.end()
        return {**base, "status": "limit_exceeded" if is_limit else "error",
                "feasible": False, "obj": None, "seconds": seconds,
                "solution": None, "conflicts": None, "error_msg": msg}
    seconds = perf_counter() - t0

    status = _status_name(model)
    feasible = sol is not None and ("OPTIMAL" in status or "FEASIBLE" in status)

    if feasible:
        solution = {e: int(round(x[e].solution_value)) for e in E}
        result = {**base, "status": status, "feasible": True,
                  "obj": round(sol.objective_value, 4), "seconds": seconds,
                  "solution": solution, "conflicts": None, "error_msg": None}
    else:
        result = {**base, "status": status, "feasible": False,
                  "obj": None, "seconds": seconds, "solution": None,
                  "conflicts": _refine_conflicts(model), "error_msg": None}

    model.end()
    return result
