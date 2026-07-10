"""Pipeline end-to-end: nạp dữ liệu -> QC vòng khép -> bình sai LSQ -> báo cáo.

SPEC.md mục 3, mục 5, mục 9 (Phase 5).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from binh_sai_do_cao.core import network_graph
from binh_sai_do_cao.core.accuracy import compute_accuracy, compute_extremes
from binh_sai_do_cao.core.adjustment import AdjustmentError, run_adjustment
from binh_sai_do_cao.core.closure_check import STATUS_FAIL, check_all_closures
from binh_sai_do_cao.core.loop_finder import find_fundamental_cycles
from binh_sai_do_cao.core.network_graph import FragmentedNetworkError
from binh_sai_do_cao.io.input_loader import InputValidationError, load_json
from binh_sai_do_cao.io.report_writer import write_report


def run_pipeline(input_path: str | Path, output_path: str | Path) -> int:
    data = load_json(input_path)

    graph = network_graph.build_graph(data)
    network_graph.check_connectivity(graph)

    loops = find_fundamental_cycles(data)
    closures = check_all_closures(loops, data.settings)

    failed = [c for c in closures if c.status == STATUS_FAIL]
    for c in failed:
        print(
            f"[CẢNH BÁO] Vòng '{c.loop.path_str}' vượt sai số khép giới hạn: "
            f"Wh={c.wh_mm:.2f}mm > Wh(gh)={c.wh_gh_mm:.2f}mm. "
            "Không tự động loại bỏ trị đo — cần người dùng kiểm tra/đo lại.",
            file=sys.stderr,
        )

    adjustment = run_adjustment(data)
    accuracy = compute_accuracy(data, adjustment)
    extremes = compute_extremes(data, accuracy)

    write_report(output_path, data, adjustment, accuracy, extremes, closures)

    print(f"Đã tạo báo cáo: {output_path}")
    print(f"Mo = {accuracy.mo_mm:.2f} mm/Tr | {len(closures)} vòng khép | "
          f"{len(failed)} vòng vượt giới hạn")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bình sai lưới độ cao (thủy chuẩn hình học) & xuất báo cáo .docx"
    )
    parser.add_argument("--input", required=True, help="Đường dẫn file JSON đầu vào (SPEC.md mục 2)")
    parser.add_argument("--output", required=True, help="Đường dẫn file .docx báo cáo đầu ra")
    args = parser.parse_args(argv)

    try:
        return run_pipeline(args.input, args.output)
    except (InputValidationError, FragmentedNetworkError, AdjustmentError, ValueError) as exc:
        print(f"[LỖI] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
