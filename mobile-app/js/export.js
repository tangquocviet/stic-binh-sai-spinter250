// Xuất dữ liệu dự án ra JSON đúng schema mục 2 của SPEC.md (import thẳng
// được vào input_loader.py) hoặc CSV — qua <a download> hoặc Web Share API.

import { listPoints, listLines, lineSummary } from "./db.js";

export async function buildProjectExport(project) {
  const points = await listPoints(project.id);
  const lines = await listLines(project.id);

  const observations = [];
  for (const line of lines) {
    const summary = await lineSummary(line.id);
    if (summary.totalStations === 0) continue; // tuyến chưa có trạm nào — bỏ qua khi xuất
    observations.push({
      id: observations.length + 1,
      from: line.fromPoint,
      to: line.toPoint,
      measured_dh_m: Number(summary.totalDhM.toFixed(6)),
      stations: summary.totalStations,
      distance_km: null,
      _line_name: line.name,
    });
  }

  return {
    project: {
      name: project.name,
      date: new Date().toISOString().slice(0, 10),
      surveyor: "",
      computer: "",
      checker: "",
    },
    settings: {
      adjustment_method: "indirect",
      closure_formula: "k_sqrt_n",
      k_coefficient_mm: 0.3,
      weight_basis: "station_count",
    },
    known_points: points.map((p) => ({ name: p.name, height_m: p.heightM })),
    observations: observations.map(({ _line_name, ...obs }) => obs),
  };
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

async function shareOrDownload(filename, blob, mimeType) {
  const file = new File([blob], filename, { type: mimeType });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file], title: filename });
      return;
    } catch (err) {
      if (err && err.name === "AbortError") return; // người dùng huỷ chia sẻ
      // rơi xuống tải file trực tiếp nếu share lỗi
    }
  }
  downloadBlob(filename, blob);
}

export async function exportProjectJson(project) {
  const data = await buildProjectExport(project);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const filename = `${project.name.replace(/[^\w\-]+/g, "_")}_${data.project.date}.json`;
  await shareOrDownload(filename, blob, "application/json");
}

function csvEscape(value) {
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export async function exportProjectCsv(project) {
  const data = await buildProjectExport(project);
  const header = ["id", "from", "to", "measured_dh_m", "stations", "distance_km"];
  const rows = [header.join(",")];
  for (const obs of data.observations) {
    rows.push(header.map((k) => csvEscape(obs[k] ?? "")).join(","));
  }
  const csv = "﻿" + rows.join("\n"); // BOM để Excel đọc đúng UTF-8
  const blob = new Blob([csv], { type: "text/csv" });
  const filename = `${project.name.replace(/[^\w\-]+/g, "_")}_${data.project.date}.csv`;
  await shareOrDownload(filename, blob, "text/csv");
}
