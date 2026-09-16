"""Đọc file Excel template (4 sheet dữ liệu) -> cấu trúc SPA chuẩn.

Trả về đối tượng Instance chứa (S, P, E, ws, wp, c, G) cho solver/bounds/visualizer,
kèm metadata (tên SV, tên đề tài, GV) để hiển thị.

Quy ước: trọng số SỐ CÀNG LỚN = CÀNG ƯU TIÊN, đọc thẳng, KHÔNG đảo.
Nếu file có lỗi cấu trúc, ném SpaValidationError chứa DANH SÁCH lỗi (báo hết một lần).
"""

from dataclasses import dataclass, field
from itertools import combinations
import math

import pandas as pd

REQUIRED_SHEETS = ["Students", "Projects", "Registrations"]
OPTIONAL_SHEETS = ["Groups"]

COLS = {
    "Students":      ["student_id", "student_name"],
    "Projects":      ["project_id", "project_name", "capacity", "supervisor"],
    "Registrations": ["student_id", "project_id", "student_pref", "supervisor_interest"],
    "Groups":        ["group_id", "student_id"],
}
REQUIRED_COLS = {
    "Students":      ["student_id"],
    "Projects":      ["project_id", "capacity"],
    "Registrations": ["student_id", "project_id"],
    "Groups":        ["group_id", "student_id"],
}


class SpaValidationError(Exception):
    """Lỗi cấu trúc/nội dung file Excel. .errors là danh sách chuỗi lỗi."""
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


@dataclass
class Instance:
    S: list                       # danh sách student_id
    P: list                       # danh sách project_id
    E: list                       # danh sách cạnh (student_id, project_id)
    ws: dict                      # {(s,p): trọng số nguyện vọng SV}
    wp: dict                      # {(s,p): điểm quan tâm của GV}
    c: dict                       # {p: capacity}
    G: list                       # danh sách cặp (i1, i2) đã bung từ nhóm
    student_name: dict = field(default_factory=dict)
    project_name: dict = field(default_factory=dict)
    supervisor: dict = field(default_factory=dict)
    groups_raw: dict = field(default_factory=dict)   # {group_id: [members]}
    warnings: list = field(default_factory=list)
    n_missing_ws: int = 0                             # số cạnh chưa có student_pref
    n_missing_wp: int = 0                             # số cạnh chưa có supervisor_interest

    def summary(self):
        return {
            "Sinh viên": len(self.S),
            "Đề tài": len(self.P),
            "Số nguyện vọng": len(self.E),
            "Nhóm": len(self.groups_raw),
            "Tổng sức chứa": sum(self.c.values()),
        }


def _clean_id(v):
    """Chuẩn hóa một ô ID về chuỗi đã strip; ô trống -> ''."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    if isinstance(v, float) and v.is_integer():   # 1.0 -> "1"
        return str(int(v)).strip()
    return str(v).strip()


def _to_int(v):
    """Ép về số nguyên nếu hợp lệ, ngược lại None."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not f.is_integer():
        return None
    return int(f)


def load_instance_from_excel(source) -> Instance:
    """source: đường dẫn file .xlsx hoặc đối tượng file-like (Streamlit uploader)."""
    errors = []
    warnings = []

    try:
        xls = pd.ExcelFile(source)
    except Exception as ex:
        raise SpaValidationError([f"Không mở được file Excel: {ex}"])

    # 1) Kiểm tra sheet bắt buộc
    for sh in REQUIRED_SHEETS:
        if sh not in xls.sheet_names:
            errors.append(f"Thiếu sheet bắt buộc: '{sh}'.")
    if errors:
        raise SpaValidationError(errors)

    def read_sheet(name):
        df = pd.read_excel(xls, sheet_name=name, dtype=object)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    df_s = read_sheet("Students")
    df_p = read_sheet("Projects")
    df_r = read_sheet("Registrations")
    df_g = read_sheet("Groups") if "Groups" in xls.sheet_names else pd.DataFrame(columns=COLS["Groups"])

    # 2) Kiểm tra cột bắt buộc
    for sh, df in [("Students", df_s), ("Projects", df_p),
                   ("Registrations", df_r), ("Groups", df_g)]:
        for col in REQUIRED_COLS[sh]:
            if col not in df.columns:
                errors.append(f"Sheet '{sh}' thiếu cột bắt buộc: '{col}'.")
    if errors:
        raise SpaValidationError(errors)

    # 3) Students
    S, student_name = [], {}
    seen_s = set()
    for _, row in df_s.iterrows():
        sid = _clean_id(row.get("student_id"))
        if sid == "":
            continue
        if sid in seen_s:
            errors.append(f"[Students] student_id trùng: '{sid}'.")
            continue
        seen_s.add(sid)
        S.append(sid)
        nm = row.get("student_name")
        student_name[sid] = _clean_id(nm) if _clean_id(nm) else sid
    if not S:
        errors.append("[Students] Không có sinh viên nào.")

    # 4) Projects
    P, c, project_name, supervisor = [], {}, {}, {}
    seen_p = set()
    for _, row in df_p.iterrows():
        pid = _clean_id(row.get("project_id"))
        if pid == "":
            continue
        if pid in seen_p:
            errors.append(f"[Projects] project_id trùng: '{pid}'.")
            continue
        cap = _to_int(row.get("capacity"))
        if cap is None or cap < 1:
            errors.append(f"[Projects] capacity của '{pid}' phải là số nguyên ≥ 1 "
                          f"(đang là: {row.get('capacity')!r}).")
            continue
        seen_p.add(pid)
        P.append(pid)
        c[pid] = cap
        nm = row.get("project_name")
        project_name[pid] = _clean_id(nm) if _clean_id(nm) else pid
        sv = row.get("supervisor")
        supervisor[pid] = _clean_id(sv)
    if not P:
        errors.append("[Projects] Không có đề tài nào hợp lệ.")

    S_set, P_set = set(S), set(P)

    # 5) Registrations -> E, ws, wp
    E, ws, wp = [], {}, {}
    seen_e = set()
    missing_ws = 0
    missing_wp = 0
    for idx, row in df_r.iterrows():
        sid = _clean_id(row.get("student_id"))
        pid = _clean_id(row.get("project_id"))
        if sid == "" and pid == "":
            continue
        line = idx + 2  # +1 header, +1 về 1-based
        if sid == "" or pid == "":
            errors.append(f"[Registrations] dòng {line}: thiếu student_id hoặc project_id.")
            continue
        if sid not in S_set:
            errors.append(f"[Registrations] dòng {line}: student_id '{sid}' không có trong sheet Students.")
            continue
        if pid not in P_set:
            errors.append(f"[Registrations] dòng {line}: project_id '{pid}' không có trong sheet Projects.")
            continue
        if (sid, pid) in seen_e:
            warnings.append(f"[Registrations] cặp trùng ({sid}, {pid}) — đã bỏ dòng lặp.")
            continue
        seen_e.add((sid, pid))
        E.append((sid, pid))

        sp = _to_int(row.get("student_pref"))
        if sp is not None:
            ws[(sid, pid)] = sp          # chỉ lưu khi có giá trị thật
        else:
            missing_ws += 1

        si = _to_int(row.get("supervisor_interest"))
        if si is not None:
            wp[(sid, pid)] = si
        else:
            missing_wp += 1

    if not E:
        errors.append("[Registrations] Không có nguyện vọng hợp lệ nào.")

    # Cảnh báo SV không đăng ký đề tài nào (sẽ gây vô nghiệm do ràng buộc gán đúng 1)
    students_with_edge = {s for s, _ in E}
    for s in S:
        if s not in students_with_edge:
            warnings.append(f"[Registrations] Sinh viên '{s}' chưa đăng ký đề tài nào "
                            f"→ có thể gây vô nghiệm.")

    # (ô trọng số để trống là hợp lệ — không cảnh báo ở bước nạp;
    #  việc thiếu trọng số chỉ liên quan khi giải MILP2/3/4, xử lý ở app.)

    # 6) Groups -> groups_raw + bung thành cặp G
    groups_raw = {}
    for idx, row in df_g.iterrows():
        gid = _clean_id(row.get("group_id"))
        sid = _clean_id(row.get("student_id"))
        if gid == "" and sid == "":
            continue
        line = idx + 2
        if gid == "" or sid == "":
            errors.append(f"[Groups] dòng {line}: thiếu group_id hoặc student_id.")
            continue
        if sid not in S_set:
            errors.append(f"[Groups] dòng {line}: student_id '{sid}' không có trong sheet Students.")
            continue
        members = groups_raw.setdefault(gid, [])
        if sid in members:
            warnings.append(f"[Groups] '{sid}' xuất hiện 2 lần trong nhóm '{gid}' — bỏ bớt.")
        else:
            members.append(sid)

    # SV nằm trong nhiều nhóm
    seen_member = {}
    for gid, members in groups_raw.items():
        for m in members:
            if m in seen_member:
                warnings.append(f"[Groups] Sinh viên '{m}' nằm trong nhiều nhóm "
                                f"('{seen_member[m]}' và '{gid}').")
            else:
                seen_member[m] = gid

    G = []
    for gid, members in groups_raw.items():
        if len(members) == 1:
            warnings.append(f"[Groups] Nhóm '{gid}' chỉ có 1 thành viên — không tạo ràng buộc.")
        for a, b in combinations(members, 2):
            G.append((a, b))

    if errors:
        raise SpaValidationError(errors)

    return Instance(
        S=S, P=P, E=E, ws=ws, wp=wp, c=c, G=G,
        student_name=student_name, project_name=project_name,
        supervisor=supervisor, groups_raw=groups_raw, warnings=warnings,
        n_missing_ws=missing_ws, n_missing_wp=missing_wp,
    )
