"""Vẽ đồ thị hai phía cho một instance SPA (bê từ spa_visualizer.py cũ).

- solution=None  -> chỉ vẽ input (một khung).
- solution=dict  -> vẽ 2 khung: input | lời giải (cạnh được chọn tô đỏ).

Đã bỏ import networkx không dùng tới; chỉ cần matplotlib + numpy.
"""

import matplotlib.pyplot as plt
import numpy as np


def visualize_spa_instance(S, P, E, ws, wp, c, G, solution=None, figsize=(14, 10),
                           show_ws=True, show_wp=True, show_groups=True):
    # Chỉ vẽ những nhãn mà mô hình thực sự dùng tới:
    #   show_ws     — trọng số nguyện vọng SV (phía sinh viên)
    #   show_wp     — điểm GV quan tâm (phía đề tài)
    #   show_groups — ràng buộc nhóm (đường cong tím)
    if solution is not None:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        axes = [ax1, ax2]
        titles = ['Dữ liệu đầu vào', 'Lời giải phân công']
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(figsize[0] // 2, figsize[1]))
        axes = [ax1]
        titles = ['Đồ thị hai phía — Sinh viên / Đề tài']

    for idx, ax in enumerate(axes):
        ax.clear()
        ax.set_xlim(-0.5, 2.5)
        ax.set_ylim(-0.5, max(len(S), len(P)) + 0.5)
        ax.axis('off')
        ax.set_title(titles[idx], fontsize=15, fontweight='bold', pad=20)

        student_positions = {}
        project_positions = {}

        student_y_spacing = (max(len(S), len(P)) - 1) / (len(S) - 1) if len(S) > 1 else 0
        project_y_spacing = (max(len(S), len(P)) - 1) / (len(P) - 1) if len(P) > 1 else 0

        for i, s in enumerate(S):
            student_positions[s] = (0.2, max(len(S), len(P)) - 1 - i * student_y_spacing)
        for i, p in enumerate(P):
            project_positions[p] = (1.8, max(len(S), len(P)) - 1 - i * project_y_spacing)

        # Cạnh
        for s, p in E:
            x1, y1 = student_positions[s]
            x2, y2 = project_positions[p]

            is_selected = False
            if solution is not None and idx == 1:
                is_selected = solution.get((s, p), 0) == 1

            if is_selected:
                color, linewidth, alpha, zorder = 'red', 3, 1.0, 10
            else:
                color, linewidth, zorder = 'gray', 1.5, 1
                alpha = 0.6 if idx == 1 else 0.8

            ax.plot([x1, x2], [y1, y2], color=color, linewidth=linewidth,
                    alpha=alpha, zorder=zorder)

            # ws (gần SV) — chỉ vẽ khi cạnh có giá trị thật
            if show_ws and (s, p) in ws:
                ws_x = x1 + (x2 - x1) * 0.15
                ws_y = y1 + (y2 - y1) * 0.15
                ax.text(ws_x, ws_y, str(ws[(s, p)]), fontsize=9, ha='center', va='center',
                        bbox=dict(boxstyle='circle,pad=0.3', facecolor='lightblue',
                                  edgecolor='blue', linewidth=0.5), zorder=zorder + 1)
            # wp (gần đề tài) — chỉ vẽ khi cạnh có giá trị thật
            if show_wp and (s, p) in wp:
                wp_x = x1 + (x2 - x1) * 0.85
                wp_y = y1 + (y2 - y1) * 0.85
                ax.text(wp_x, wp_y, str(wp[(s, p)]), fontsize=9, ha='center', va='center',
                        bbox=dict(boxstyle='circle,pad=0.3', facecolor='lightgreen',
                                  edgecolor='green', linewidth=0.5), zorder=zorder + 1)

        # Ràng buộc nhóm (đường cong tím bên trái)
        for s1, s2 in (G if show_groups else []):
            y1 = student_positions[s1][1]
            y2 = student_positions[s2][1]
            y_mid = (y1 + y2) / 2
            ctrl_x = -0.15 - 0.2
            t = np.linspace(0, 1, 50)
            xc = (1 - t) ** 2 * 0.2 + 2 * (1 - t) * t * ctrl_x + t ** 2 * 0.2
            yc = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * y_mid + t ** 2 * y2
            ax.plot(xc, yc, 'purple', linewidth=2.5, alpha=0.7, linestyle='--', zorder=5)
            ax.plot(0.2, y1, 'o', color='purple', markersize=6, zorder=6)
            ax.plot(0.2, y2, 'o', color='purple', markersize=6, zorder=6)

        # Nút SV
        for s in S:
            x, y = student_positions[s]
            ax.add_patch(plt.Circle((x, y), 0.12, color='white', ec='black',
                                    linewidth=2, zorder=20))
            ax.text(x, y, s, fontsize=11, ha='center', va='center',
                    fontweight='bold', zorder=21)

        # Nút đề tài + sức chứa
        for p in P:
            x, y = project_positions[p]
            ax.add_patch(plt.Circle((x, y), 0.12, color='white', ec='black',
                                    linewidth=2, zorder=20))
            ax.text(x, y, p, fontsize=11, ha='center', va='center',
                    fontweight='bold', zorder=21)
            ax.text(x + 0.25, y, f"({c[p]})", fontsize=10, ha='left',
                    va='center', style='italic', zorder=21)

        # Nhãn cột
        legend_y = max(len(S), len(P)) + 0.3
        ax.text(0.2, legend_y, "Sinh viên", fontsize=12, ha='center', fontweight='bold')
        ax.text(1.8, legend_y, "Đề tài (sức chứa)", fontsize=12, ha='center', fontweight='bold')

        # Chú thích trọng số
        legend_y2 = -0.3
        if show_ws:
            ax.text(0.5, legend_y2, "● ws (nguyện vọng SV)", fontsize=9, color='blue', ha='left')
        if show_wp:
            ax.text(1.3, legend_y2, "● wp (GV quan tâm)", fontsize=9, color='green', ha='left')
        if show_groups and len(G) > 0:
            ax.text(0.5, legend_y2 - 0.15, "-- Ràng buộc nhóm", fontsize=9,
                    color='purple', ha='left')
        if idx == 1:
            ax.text(1.3, legend_y2 - 0.15, "━ Được phân công", fontsize=9,
                    color='red', ha='left')

    plt.tight_layout()
    return fig
