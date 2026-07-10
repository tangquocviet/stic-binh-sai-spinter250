"""TC-13 (SPEC.md mục 6.1) — bảng động co giãn đúng số hàng theo dữ liệu."""

from __future__ import annotations

from pathlib import Path

from binh_sai_do_cao.core.accuracy import compute_accuracy, compute_extremes
from binh_sai_do_cao.core.adjustment import run_adjustment
from binh_sai_do_cao.core.closure_check import check_all_closures
from binh_sai_do_cao.core.loop_finder import find_fundamental_cycles
from binh_sai_do_cao.io.input_loader import load_json
from binh_sai_do_cao.io.report_writer import build_report

FIXTURES = Path(__file__).parent / "fixtures"


def test_tc13_dynamic_table_row_counts(tmp_path):
    data = load_json(FIXTURES / "cua_dai_input.json")
    adjustment = run_adjustment(data)
    accuracy = compute_accuracy(data, adjustment)
    extremes = compute_extremes(data, accuracy)
    loops = find_fundamental_cycles(data)
    closures = check_all_closures(loops, data.settings)

    doc = build_report(data, adjustment, accuracy, extremes, closures)

    assert len(doc.tables) == 3
    known_table, adjusted_table, obs_table = doc.tables
    # +1 dòng tiêu đề
    assert len(known_table.rows) == len(data.known_points) + 1
    assert len(adjusted_table.rows) == len(adjustment.unknown_names) + 1
    assert len(obs_table.rows) == len(data.observations) + 1

    out_path = tmp_path / "report.docx"
    doc.save(str(out_path))
    assert out_path.exists() and out_path.stat().st_size > 0
