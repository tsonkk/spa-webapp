"""Cận trên (Upper Bound) cho từng mô hình MILP — đúng công thức trong bài báo.

    UB1 = min(|S|, sum_j c_j)
    UB2 = sum_i max_{j:(i,j)∈E} ws_ij
    UB3 = sum_i max_{j:(i,j)∈E} (ws_ij + wp_ij)
    UB4 = sum_{(i1,i2)∈G} max_{j: (i1,j),(i2,j)∈E} (ws_i1j+wp_i1j+ws_i2j+wp_i2j)
          + sum_{i∉G} max_{j:(i,j)∈E} (ws_ij + wp_ij)

GAP(%) = (UB - OBJ) / UB * 100
"""


def compute_ub1(S, P, E, ws, wp, c, G):
    return min(len(S), sum(c[j] for j in P))


def compute_ub2(S, P, E, ws, wp, c, G):
    total = 0
    for i in S:
        vals = [ws.get((i, j), 0) for j in P if (i, j) in E]
        if vals:
            total += max(vals)
    return total


def compute_ub3(S, P, E, ws, wp, c, G):
    total = 0
    for i in S:
        vals = [ws.get((i, j), 0) + wp.get((i, j), 0) for j in P if (i, j) in E]
        if vals:
            total += max(vals)
    return total


def compute_ub4(S, P, E, ws, wp, c, G):
    students_in_group = set(i for pair in G for i in pair)
    ub = 0
    for (i1, i2) in G:
        common = [j for j in P if (i1, j) in E and (i2, j) in E]
        if common:
            ub += max(ws.get((i1, j), 0) + wp.get((i1, j), 0) +
                      ws.get((i2, j), 0) + wp.get((i2, j), 0)
                      for j in common)
    for i in S:
        if i not in students_in_group:
            vals = [ws.get((i, j), 0) + wp.get((i, j), 0) for j in P if (i, j) in E]
            if vals:
                ub += max(vals)
    return ub


# Dispatcher tiện lợi: chọn UB theo model_id
_UB_FUNCS = {1: compute_ub1, 2: compute_ub2, 3: compute_ub3, 4: compute_ub4}


def compute_ub(model_id, S, P, E, ws, wp, c, G):
    """Trả về cận trên UB tương ứng với model_id (1..4)."""
    return _UB_FUNCS[model_id](S, P, E, ws, wp, c, G)
