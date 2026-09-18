"""SPA Web App — mô phỏng quy trình phân công Sinh viên – Đề tài của Khoa.

Chạy:  streamlit run app.py

Quy trình 4 bước:
    Bước 1 — Danh sách sinh viên
    Bước 2 — Danh sách đề tài & sức chứa
    Bước 3 — Nguyện vọng đăng ký (+ trọng số, nhóm)
    Bước 4 — Phân công (chọn MILP1/2/3/4 -> giải bằng CPLEX)

App chỉ IMPORT + HIỂN THỊ dữ liệu từ file Excel; muốn sửa thì sửa Excel rồi nạp lại.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from core import (
    load_instance_from_excel, SpaValidationError,
    compute_ub, solve_spa, format_duration, MODEL_NAMES,
    visualize_spa_instance,
)

TEMPLATE_PATH = Path(__file__).parent / "data" / "template_spa.xlsx"

st.set_page_config(page_title="SPA — Phân công SV & Đề tài", page_icon="🎓", layout="wide")


# ────────────────────────────────────────────────────────────────────────────
# Sidebar: nạp dữ liệu
# ────────────────────────────────────────────────────────────────────────────
def load_into_state(source, name):
    try:
        inst = load_instance_from_excel(source)
    except SpaValidationError as ex:
        st.session_state.instance = None
        st.session_state.load_errors = ex.errors
        st.session_state.source_name = None
        return
    st.session_state.instance = inst
    st.session_state.load_errors = None
    st.session_state.source_name = name
    st.session_state.result = None  # xóa kết quả cũ khi đổi dữ liệu


st.session_state.setdefault("instance", None)
st.session_state.setdefault("load_errors", None)
st.session_state.setdefault("source_name", None)
st.session_state.setdefault("result", None)

with st.sidebar:
    st.header("📂 Nạp dữ liệu")
    up = st.file_uploader("Chọn file Excel (.xlsx)", type=["xlsx"])
    if up is not None:
        if st.button("⬆️ Nạp file này", width='stretch'):
            load_into_state(up, up.name)

    if TEMPLATE_PATH.exists():
        if st.button("📄 Dùng dữ liệu mẫu (ví dụ trong bài)", width='stretch'):
            load_into_state(str(TEMPLATE_PATH), "template_spa.xlsx (mẫu)")
        with open(TEMPLATE_PATH, "rb") as f:
            st.download_button("⬇️ Tải file template mẫu", f.read(),
                               file_name="template_spa.xlsx", width='stretch')

    st.divider()
    inst = st.session_state.instance
    if inst is not None:
        st.success(f"Đã nạp: **{st.session_state.source_name}**")
        for k, v in inst.summary().items():
            st.caption(f"• {k}: **{v}**")
    else:
        st.info("Chưa có dữ liệu. Hãy nạp file Excel hoặc dùng dữ liệu mẫu.")


# ────────────────────────────────────────────────────────────────────────────
# Header
# ────────────────────────────────────────────────────────────────────────────
st.title("🎓 Phân công Sinh viên – Đề tài (SPA)")
st.caption("Công cụ minh họa & kiểm chứng mô hình MILP · giải bằng CPLEX")

if st.session_state.load_errors:
    st.error("File Excel có lỗi — vui lòng sửa rồi nạp lại:")
    for e in st.session_state.load_errors:
        st.markdown(f"- {e}")

inst = st.session_state.instance
if inst is None:
    st.stop()

if inst.warnings:
    with st.expander(f"⚠️ {len(inst.warnings)} cảnh báo (không chặn giải)", expanded=False):
        for w in inst.warnings:
            st.markdown(f"- {w}")


# ────────────────────────────────────────────────────────────────────────────
# Helpers hiển thị
# ────────────────────────────────────────────────────────────────────────────
def students_df(inst):
    return pd.DataFrame(
        [{"student_id": s, "student_name": inst.student_name.get(s, "")} for s in inst.S]
    )


def projects_df(inst):
    return pd.DataFrame(
        [{"project_id": p, "project_name": inst.project_name.get(p, ""),
          "capacity": inst.c[p], "supervisor": inst.supervisor.get(p, "")} for p in inst.P]
    )


def registrations_df(inst):
    return pd.DataFrame(
        [{"student_id": s, "project_id": p,
          "student_pref (ws)": inst.ws.get((s, p), ""),
          "supervisor_interest (wp)": inst.wp.get((s, p), "")} for (s, p) in inst.E]
    )


def groups_df(inst):
    rows = [{"group_id": g, "student_id": m}
            for g, members in inst.groups_raw.items() for m in members]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["group_id", "student_id"])


def show_graph(inst, solution=None, show_ws=True, show_wp=True, show_groups=True):
    fig = visualize_spa_instance(
        inst.S, inst.P, inst.E, inst.ws, inst.wp, inst.c, inst.G,
        solution=solution, figsize=(14, 9),
        show_ws=show_ws, show_wp=show_wp, show_groups=show_groups,
    )
    st.pyplot(fig)
    plt.close(fig)


# Đồ thị lời giải chỉ hiện thông tin mà mô hình đó dùng tới:
#   (show_ws, show_wp, show_groups) theo model_id
GRAPH_FLAGS = {
    1: (False, False, False),   # MILP1: chỉ cạnh
    2: (True,  False, False),   # MILP2: + ws
    3: (True,  True,  False),   # MILP3: + ws + wp
    4: (True,  True,  True),    # MILP4: + ws + wp + nhóm
}


# ────────────────────────────────────────────────────────────────────────────
# 4 bước
# ────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "① Danh sách sinh viên",
    "② Đề tài & sức chứa",
    "③ Nguyện vọng đăng ký",
    "④ Phân công (giải MILP)",
])

with tab1:
    st.subheader("Bước 1 — Danh sách sinh viên")
    st.caption("Khoa lập danh sách sinh viên đăng ký làm đề tài.")
    st.dataframe(students_df(inst), width='stretch', hide_index=True)

with tab2:
    st.subheader("Bước 2 — Danh sách đề tài & sức chứa")
    st.caption("GV nộp đề tài, mỗi đề tài có sức chứa tối đa (capacity).")
    st.dataframe(projects_df(inst), width='stretch', hide_index=True)

with tab3:
    st.subheader("Bước 3 — Nguyện vọng đăng ký")
    st.caption("Mỗi SV đăng ký ≥ 1 đề tài. ws = nguyện vọng SV, wp = GV quan tâm "
               "(số càng lớn càng ưu tiên).")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("**Bảng nguyện vọng**")
        st.dataframe(registrations_df(inst), width='stretch', hide_index=True)
        st.markdown("**Nhóm (học chung đề tài)**")
        st.dataframe(groups_df(inst), width='stretch', hide_index=True)
    with c2:
        st.markdown("**Đồ thị hai phía (dữ liệu đầu vào)**")
        show_graph(inst, solution=None)

with tab4:
    st.subheader("Bước 4 — Phân công")
    st.caption("Chọn mô hình MILP rồi để CPLEX tìm lời giải tối ưu.")

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        model_id = st.selectbox(
            "Mô hình", options=[1, 2, 3, 4],
            format_func=lambda m: MODEL_NAMES[m],
        )

    # Kiểm tra dữ liệu bắt buộc theo mô hình -> CHẶN nếu thiếu
    block_msgs = []
    if model_id >= 2 and inst.n_missing_ws:
        block_msgs.append(
            f"**MILP{model_id}** cần điểm **nguyện vọng sinh viên (student_pref)** cho tất cả "
            f"đăng ký, nhưng ở sheet **Registrations** còn **{inst.n_missing_ws} dòng** chưa điền "
            f"cột `student_pref`. Vui lòng điền đủ rồi nạp lại file.")
    if model_id >= 3 and inst.n_missing_wp:
        block_msgs.append(
            f"**MILP{model_id}** cần điểm **quan tâm của giảng viên (supervisor_interest)** cho tất cả "
            f"đăng ký, nhưng ở sheet **Registrations** còn **{inst.n_missing_wp} dòng** chưa điền "
            f"cột `supervisor_interest`. Vui lòng điền đủ rồi nạp lại file.")
    if model_id == 4 and not inst.G:
        block_msgs.append(
            "**MILP4** cần **thông tin nhóm**, nhưng sheet **Groups** chưa có nhóm hợp lệ nào "
            "(mỗi nhóm cần ít nhất 2 sinh viên). Vui lòng khai báo nhóm rồi nạp lại file.")

    with col_btn:
        st.write("")
        st.write("")
        run = st.button("▶️ Giải bằng CPLEX", type="primary",
                        width='stretch', disabled=bool(block_msgs))

    if block_msgs:
        st.error("Chưa đủ dữ liệu để giải mô hình này:")
        for m in block_msgs:
            st.markdown(f"- {m}")

    if run and not block_msgs:
        ub = compute_ub(model_id, inst.S, inst.P, inst.E, inst.ws, inst.wp, inst.c, inst.G)
        with st.spinner("Đang giải bằng CPLEX…"):
            res = solve_spa(model_id, inst.S, inst.P, inst.E,
                            inst.ws, inst.wp, inst.c, inst.G)
        res["ub"] = ub
        st.session_state.result = res

    # Chỉ hiển thị kết quả nếu nó thuộc đúng mô hình đang chọn
    # (đổi model hoặc model đang bị chặn -> không hiện kết quả cũ)
    res = st.session_state.result
    if res is not None and res.get("model_id") == model_id:
        st.markdown(f"##### Kết quả — {MODEL_NAMES[res['model_id']]}")

        if res["status"] == "limit_exceeded":
            st.error(
                f"⚠️ Instance quá lớn cho **CPLEX Community Edition** (giới hạn 1000 biến "
                f"/ 1000 ràng buộc). Mô hình này có **{res['n_vars']} biến, {res['n_cons']} "
                f"ràng buộc**.")
            st.info("Bản chạy trên host miễn phí dùng CPLEX Community nên bị giới hạn kích thước. "
                    "Với instance lớn, hãy chạy app ở máy có **CPLEX đầy đủ (bản academic)**.")
        elif res["status"] == "error":
            st.error("❌ Có lỗi khi giải:")
            st.code(res.get("error_msg") or "(không rõ)")
        elif not res["feasible"]:
            st.error(f"❌ Vô nghiệm (status: {res['status']}). "
                     f"Thời gian: {format_duration(res['seconds'])}")
            st.markdown("**Ràng buộc xung đột (ConflictRefiner):**")
            for cf in (res["conflicts"] or []):
                st.markdown(f"- `{cf}`")
            st.info("Gợi ý: tăng capacity đề tài, hoặc nới/bỏ bớt ràng buộc nhóm ở sheet Groups.")
        else:
            ub = res["ub"]
            obj = res["obj"]
            gap = (ub - obj) / ub * 100 if ub and ub > 0 else 0.0
            obj_disp = int(obj) if float(obj).is_integer() else obj

            def metric(col, label, value):
                col.markdown(
                    "<div style='line-height:1.35'>"
                    f"<div style='font-size:0.8rem;color:#808495'>{label}</div>"
                    f"<div style='font-size:1.6rem;font-weight:700'>{value}</div>"
                    "</div>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            metric(m1, "OBJ (giá trị mục tiêu)", obj_disp)
            metric(m2, "UB (cận trên)", int(ub) if float(ub).is_integer() else ub)
            metric(m3, "GAP", f"{gap:.2f}%")
            metric(m4, "Thời gian giải", format_duration(res["seconds"]))

            # Bảng phân công
            assign = {s: p for (s, p), v in res["solution"].items() if v == 1}
            rows = []
            for s in inst.S:
                p = assign.get(s)
                rows.append({
                    "student_id": s,
                    "student_name": inst.student_name.get(s, ""),
                    "→ project_id": p if p else "(chưa gán)",
                    "project_name": inst.project_name.get(p, "") if p else "",
                    "ws": inst.ws.get((s, p), "") if p else "",
                    "wp": inst.wp.get((s, p), "") if p else "",
                })
            st.markdown("**Bảng phân công**")
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

            st.markdown("**Đồ thị lời giải** (đường phân công được tô đỏ)")
            sw, swp, sg = GRAPH_FLAGS[res["model_id"]]
            show_graph(inst, solution=res["solution"],
                       show_ws=sw, show_wp=swp, show_groups=sg)
