import * as db from "./db.js";
import { checkClosure, STATUS_OK, FLAG_NEAR_LIMIT, FLAG_OVER_LIMIT } from "./closure.js";
import { exportProjectJson, exportProjectCsv } from "./export.js";

const app = document.getElementById("app");
const toastEl = document.getElementById("toast");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

let toastTimer = null;
function toast(message, type = "") {
  toastEl.textContent = message;
  toastEl.className = "toast" + (type ? " " + type : "");
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastEl.hidden = true;
  }, 4000);
}

function fmt4(x) {
  return Number(x).toFixed(4);
}
function fmtMm(x) {
  return (Number(x) >= 0 ? "+" : "") + Number(x).toFixed(2);
}

// ---------------- Router ----------------

async function router() {
  const hash = location.hash.slice(1) || "/";
  const parts = hash.split("/").filter(Boolean);

  try {
    if (parts.length === 0) {
      await renderProjects();
    } else if (parts[0] === "project" && parts.length === 2) {
      await renderProjectDetail(Number(parts[1]));
    } else if (parts[0] === "project" && parts.length === 3 && parts[2] === "export") {
      await renderExport(Number(parts[1]));
    } else if (parts[0] === "line" && parts.length === 2) {
      await renderLineDetail(Number(parts[1]));
    } else {
      await renderProjects();
    }
  } catch (err) {
    console.error(err);
    app.innerHTML = `<div class="card"><p>Lỗi: ${esc(err.message)}</p></div>`;
  }
}

window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);

function topbar(title, backHref) {
  return `
    <header class="topbar">
      ${backHref ? `<a class="btn-back" href="#${backHref}">‹</a>` : ""}
      <h1>${esc(title)}</h1>
    </header>`;
}

// ---------------- Màn 1: Danh sách dự án ----------------

async function renderProjects() {
  const projects = await db.listProjects();
  app.innerHTML = `
    ${topbar("Dự án đo đạc")}
    <div id="list">
      ${
        projects.length
          ? projects
              .map(
                (p) => `
        <div class="list-item">
          <a class="list-item-link" href="#/project/${p.id}">
            <div><strong>${esc(p.name)}</strong></div>
            <div class="meta">${new Date(p.createdAt).toLocaleDateString("vi-VN")}</div>
          </a>
          <button class="btn btn-danger" data-action="delete-project" data-id="${p.id}">Xoá</button>
        </div>`
              )
              .join("")
          : `<p class="empty-hint">Chưa có dự án nào. Bấm nút + để tạo dự án mới.</p>`
      }
    </div>
    <button class="fab-add" data-action="new-project">+</button>
  `;

  app.querySelector('[data-action="new-project"]').addEventListener("click", async () => {
    const name = prompt("Tên dự án (VD: Cầu Cửa Đại lần 3):");
    if (!name || !name.trim()) return;
    const id = await db.createProject(name.trim());
    location.hash = `#/project/${id}`;
  });

  app.querySelectorAll('[data-action="delete-project"]').forEach((btn) =>
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!confirm("Xoá dự án này và toàn bộ tuyến/trạm đo bên trong?")) return;
      await db.deleteProject(Number(btn.dataset.id));
      renderProjects();
    })
  );
}

// ---------------- Màn 2: Chi tiết dự án (điểm gốc + tuyến đo) ----------------

async function renderProjectDetail(projectId) {
  const projects = await db.listProjects();
  const project = projects.find((p) => p.id === projectId);
  if (!project) {
    location.hash = "#/";
    return;
  }
  const [points, lines] = await Promise.all([db.listPoints(projectId), db.listLines(projectId)]);

  const lineRowsHtml = [];
  for (const line of lines) {
    const summary = await db.lineSummary(line.id);
    let badge = "";
    if (summary.closed && summary.totalStations > 0) {
      const c = checkClosure(summary.totalDhM * 1000, summary.totalStations);
      const cls = c.status === STATUS_OK ? (c.flag === FLAG_NEAR_LIMIT ? "badge-warn" : "badge-ok") : "badge-fail";
      badge = `<span class="badge ${cls}">Wh=${fmtMm(c.whMm)}mm</span>`;
    }
    lineRowsHtml.push(`
      <div class="list-item">
        <a class="list-item-link" href="#/line/${line.id}">
          <div><strong>${esc(line.fromPoint)} → ${esc(line.toPoint)}</strong> ${badge}</div>
          <div class="meta">${esc(line.name)} · ${summary.totalStations} trạm · Δh=${fmt4(summary.totalDhM)}m</div>
        </a>
        <button class="btn btn-danger" data-action="delete-line" data-id="${line.id}">Xoá</button>
      </div>`);
  }

  app.innerHTML = `
    ${topbar(project.name, "/")}

    <div class="card">
      <div class="section-title">Điểm gốc (đã biết độ cao)</div>
      ${
        points.length
          ? points
              .map(
                (p) => `
        <div class="station-row">
          <span>${esc(p.name)}</span>
          <span class="dh">${fmt4(p.heightM)} m
            <button class="btn btn-danger" style="padding:4px 8px;margin-left:8px" data-action="delete-point" data-id="${p.id}">×</button>
          </span>
        </div>`
              )
              .join("")
          : `<p class="empty-hint">Chưa có điểm gốc.</p>`
      }
      <button class="btn btn-secondary btn-block" data-action="new-point">+ Thêm điểm gốc</button>
    </div>

    <div class="section-title">Tuyến đo</div>
    <div id="lines">
      ${lineRowsHtml.length ? lineRowsHtml.join("") : `<p class="empty-hint">Chưa có tuyến đo nào.</p>`}
    </div>

    <a class="btn btn-secondary btn-block" href="#/project/${project.id}/export">Xuất dữ liệu dự án</a>

    <button class="fab-add" data-action="new-line">+</button>
  `;

  app.querySelector('[data-action="new-point"]').addEventListener("click", async () => {
    const name = prompt("Tên điểm gốc:");
    if (!name || !name.trim()) return;
    const heightStr = prompt("Độ cao (m), VD 0.7614:");
    const height = Number(heightStr);
    if (heightStr === null || Number.isNaN(height)) return;
    await db.createPoint(projectId, name.trim(), height);
    renderProjectDetail(projectId);
  });

  app.querySelectorAll('[data-action="delete-point"]').forEach((btn) =>
    btn.addEventListener("click", async () => {
      await db.deletePoint(Number(btn.dataset.id));
      renderProjectDetail(projectId);
    })
  );

  app.querySelector('[data-action="new-line"]').addEventListener("click", async () => {
    const fromPoint = prompt("Điểm đầu tuyến:");
    if (!fromPoint || !fromPoint.trim()) return;
    const toPoint = prompt("Điểm cuối tuyến (giống điểm đầu nếu là tuyến khép kín):");
    if (!toPoint || !toPoint.trim()) return;
    const name = `${fromPoint.trim()} → ${toPoint.trim()}`;
    const id = await db.createLine(projectId, name, fromPoint.trim(), toPoint.trim());
    location.hash = `#/line/${id}`;
  });

  app.querySelectorAll('[data-action="delete-line"]').forEach((btn) =>
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!confirm("Xoá tuyến này và toàn bộ trạm đo bên trong?")) return;
      await db.deleteLine(Number(btn.dataset.id));
      renderProjectDetail(projectId);
    })
  );
}

// ---------------- Màn 3+4: Nhập trạm đo + Tổng hợp tuyến ----------------

let isRows = []; // trạng thái tạm của các dòng điểm ngắm giữa đang nhập
let editingStationId = null; // id trạm đang sửa, null nếu đang nhập trạm mới

async function renderLineDetail(lineId) {
  const line = await db.getLine(lineId);
  if (!line) {
    location.hash = "#/";
    return;
  }
  const summary = await db.lineSummary(lineId);

  let editingStation = null;
  if (editingStationId != null) {
    editingStation = summary.stations.find((s) => s.id === editingStationId) || null;
    if (!editingStation) editingStationId = null; // đã bị xoá ở nơi khác
  }

  // Độ cao tương đối tích luỹ ngay trước trạm đang thao tác (để tính live-preview)
  let runningHeightBefore;
  if (editingStation) {
    runningHeightBefore = summary.stations
      .filter((s) => s.orderIndex < editingStation.orderIndex)
      .reduce((sum, s) => sum + db.stationDhM(s), 0);
    isRows = editingStation.isList.map((r) => ({ point: r.point, readingM: String(r.readingM) }));
  } else {
    runningHeightBefore = summary.totalDhM;
    isRows = [];
  }

  const formTitle = editingStation
    ? `Sửa trạm đo #${editingStation.orderIndex}`
    : `Nhập trạm đo #${summary.totalStations + 1}`;
  const saveLabel = editingStation ? "Cập nhật trạm đo" : "Lưu trạm đo";

  app.innerHTML = `
    ${topbar(line.name, `/project/${line.projectId}`)}

    <div class="card" id="stationFormCard">
      <div class="section-title">${formTitle}</div>

      <label>Điểm ngắm sau (BS)</label>
      <div class="row">
        <input type="text" id="bsPoint" placeholder="Tên điểm" value="${editingStation ? esc(editingStation.bsPoint) : ""}" />
        <input type="number" inputmode="decimal" step="0.0001" id="bsReading" placeholder="Số đọc (m)" value="${editingStation ? editingStation.bsReadingM : ""}" />
      </div>

      <div id="isRowsContainer"></div>
      <button class="btn btn-secondary" id="addIsBtn" type="button">+ Điểm ngắm giữa (IS)</button>

      <label>Điểm ngắm trước (FS)</label>
      <div class="row">
        <input type="text" id="fsPoint" placeholder="Tên điểm" value="${editingStation ? esc(editingStation.fsPoint) : ""}" />
        <input type="number" inputmode="decimal" step="0.0001" id="fsReading" placeholder="Số đọc (m)" value="${editingStation ? editingStation.fsReadingM : ""}" />
      </div>

      <label>Ghi chú (tuỳ chọn)</label>
      <input type="text" id="note" placeholder="Thời tiết, sự cố..." value="${editingStation ? esc(editingStation.note) : ""}" />

      <div class="live-preview" id="livePreview">— <span class="unit">chênh cao trạm (m)</span></div>

      <div class="row">
        <button class="btn btn-primary btn-block" id="saveStationBtn">${saveLabel}</button>
        ${editingStation ? `<button class="btn btn-secondary" id="cancelEditBtn" type="button" style="flex:0 0 auto">Huỷ</button>` : ""}
      </div>
    </div>

    <div class="card">
      <div class="section-title">Tổng hợp tuyến</div>
      <table class="summary">
        <tr><td>Số trạm đã đo</td><td>${summary.totalStations}</td></tr>
        <tr><td>Tổng chênh cao (Δh)</td><td>${fmt4(summary.totalDhM)} m</td></tr>
        <tr><td>Tuyến khép kín?</td><td>${summary.closed ? "Có" : "Không"}</td></tr>
      </table>
      <div id="closureBox"></div>
      ${whExplainHtml(summary)}
    </div>

    <div class="card">
      <div class="section-title">Các trạm đã đo</div>
      <div id="stationList">
        ${
          summary.stations.length
            ? summary.stations
                .map((s) => {
                  const dh = db.stationDhM(s);
                  const isNote = s.isList.length
                    ? ` · +${s.isList.length} IS (${s.isList.map((r) => `${esc(r.point)}=${fmt4(r.readingM)}`).join(", ")})`
                    : "";
                  return `<div class="station-row" style="flex-direction:column;align-items:stretch;gap:4px">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                      <span><strong>#${s.orderIndex}</strong> ${esc(s.bsPoint)} → ${esc(s.fsPoint)}</span>
                      <span class="dh">${fmtMm(dh * 1000)}mm</span>
                    </div>
                    <div class="meta">BS ${esc(s.bsPoint)} = ${fmt4(s.bsReadingM)}m &nbsp;·&nbsp; FS ${esc(s.fsPoint)} = ${fmt4(s.fsReadingM)}m${isNote}</div>
                    <div class="row" style="margin-top:4px">
                      <button class="btn btn-secondary" style="padding:8px" data-action="edit-station" data-id="${s.id}">✎ Sửa</button>
                      <button class="btn btn-danger" style="padding:8px" data-action="delete-station" data-id="${s.id}">Xoá</button>
                    </div>
                  </div>`;
                })
                .join("")
            : `<p class="empty-hint">Chưa có trạm nào.</p>`
        }
      </div>
    </div>
  `;

  renderClosureBox(summary);
  renderIsRows();
  wireLiveInputs(runningHeightBefore);
  updateLivePreview(runningHeightBefore); // hiện sẵn giá trị khi đang sửa trạm có sẵn số liệu

  document.getElementById("addIsBtn").addEventListener("click", () => {
    isRows.push({ point: "", readingM: "" });
    renderIsRows();
    wireLiveInputs(runningHeightBefore);
  });

  document.getElementById("saveStationBtn").addEventListener("click", () =>
    saveStation(lineId, runningHeightBefore)
  );

  const cancelBtn = document.getElementById("cancelEditBtn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      editingStationId = null;
      renderLineDetail(lineId);
    });
  }

  app.querySelectorAll('[data-action="delete-station"]').forEach((btn) =>
    btn.addEventListener("click", async () => {
      if (!confirm("Xoá trạm đo này?")) return;
      const id = Number(btn.dataset.id);
      if (editingStationId === id) editingStationId = null;
      await db.deleteStation(id);
      renderLineDetail(lineId);
    })
  );

  app.querySelectorAll('[data-action="edit-station"]').forEach((btn) =>
    btn.addEventListener("click", () => {
      editingStationId = Number(btn.dataset.id);
      renderLineDetail(lineId).then(() => {
        document.getElementById("stationFormCard").scrollIntoView({ behavior: "smooth" });
      });
    })
  );
}

const K_COEFFICIENT_MM = 0.3;

function whExplainHtml(summary) {
  const n = summary.totalStations;
  const whGh = n > 0 ? K_COEFFICIENT_MM * Math.sqrt(n) : null;
  const whActual = n > 0 ? (summary.totalDhM * 1000).toFixed(2) : null;

  return `
    <details style="margin-top:12px">
      <summary style="cursor:pointer;color:var(--text-dim)">ℹ️ Cách tính Wh và Wh(gh)</summary>
      <div style="margin-top:8px;font-size:0.9rem;color:var(--text-dim);line-height:1.5">
        <p><strong>Wh</strong> (sai số khép độ cao) — chỉ tính được khi tuyến <em>khép kín</em>
        (điểm cuối trùng điểm đầu): cộng dồn có dấu chênh cao (Δh) của tất cả các trạm đi hết
        vòng. Nếu đo hoàn hảo, đi hết vòng phải quay lại đúng độ cao ban đầu → Wh = 0.
        Wh càng lớn nghĩa là sai số tích luỹ trong tuyến càng lớn.</p>
        <p style="font-family:monospace">Wh = Σ Δh(mm) = Σ [BS(m) − FS(m)] × 1000</p>
        <p><strong>Wh(gh)</strong> (sai số khép giới hạn cho phép) — ngưỡng để đánh giá Wh có
        chấp nhận được không, phụ thuộc số trạm đo N: càng nhiều trạm, sai số ngẫu nhiên tích
        luỹ càng lớn nên ngưỡng cho phép cũng tăng theo căn bậc hai của N.</p>
        <p style="font-family:monospace">Wh(gh) = k × √N &nbsp; (k = ${K_COEFFICIENT_MM} mm, mặc định)</p>
        <p><strong>Kết luận:</strong> |Wh| ≤ Wh(gh) → Đạt. |Wh|/Wh(gh) ≥ 0.9 → cảnh báo
        "sát giới hạn" (nên đo lại nếu có thể). |Wh| &gt; Wh(gh) → Không đạt, phải đo lại.</p>
        ${
          n > 0
            ? `<p><strong>Với tuyến này:</strong> N = ${n} trạm → Wh(gh) = ${K_COEFFICIENT_MM} × √${n} = ±${whGh.toFixed(2)} mm.
               Wh thực đo = ${whActual} mm.</p>`
            : `<p>Tuyến chưa có trạm nào — nhập trạm đo để xem ví dụ tính theo số liệu thực tế.</p>`
        }
      </div>
    </details>`;
}

function renderClosureBox(summary) {
  const box = document.getElementById("closureBox");
  if (!summary.closed || summary.totalStations === 0) {
    box.innerHTML = "";
    return;
  }
  const c = checkClosure(summary.totalDhM * 1000, summary.totalStations);
  const cls = c.status === STATUS_OK ? (c.flag === FLAG_NEAR_LIMIT ? "badge-warn" : "badge-ok") : "badge-fail";
  box.innerHTML = `
    <p style="margin-top:12px">
      <span class="badge ${cls}">${c.status}${c.flag ? " — " + c.flag : ""}</span><br/>
      Wh = ${fmtMm(c.whMm)} mm &nbsp; Wh(gh) = ±${c.whGhMm.toFixed(2)} mm
    </p>`;
  if (c.status !== STATUS_OK || c.flag === FLAG_NEAR_LIMIT) {
    toast(
      c.status !== STATUS_OK
        ? `Tuyến vượt sai số khép giới hạn! Wh=${fmtMm(c.whMm)}mm > Wh(gh)=±${c.whGhMm.toFixed(2)}mm — nên đo lại.`
        : `Tuyến sát giới hạn sai số khép (Wh=${fmtMm(c.whMm)}mm, Wh(gh)=±${c.whGhMm.toFixed(2)}mm).`,
      c.status !== STATUS_OK ? "danger" : "warn"
    );
  }
}

function renderIsRows() {
  const container = document.getElementById("isRowsContainer");
  container.innerHTML = isRows
    .map(
      (row, i) => `
    <div class="is-row">
      <input type="text" class="is-point" data-i="${i}" placeholder="Tên điểm IS" value="${esc(row.point)}" />
      <input type="number" inputmode="decimal" step="0.0001" class="is-reading" data-i="${i}" placeholder="Số đọc (m)" value="${esc(row.readingM)}" />
      <button class="btn btn-danger" data-i="${i}" data-remove-is="1" type="button">×</button>
    </div>`
    )
    .join("");

  container.querySelectorAll(".is-point").forEach((el) =>
    el.addEventListener("input", (e) => {
      isRows[Number(e.target.dataset.i)].point = e.target.value;
    })
  );
  container.querySelectorAll(".is-reading").forEach((el) =>
    el.addEventListener("input", (e) => {
      isRows[Number(e.target.dataset.i)].readingM = e.target.value;
      updateLivePreview(Number(document.body.dataset.runningHeight || 0));
    })
  );
  container.querySelectorAll("[data-remove-is]").forEach((el) =>
    el.addEventListener("click", () => {
      isRows.splice(Number(el.dataset.i), 1);
      renderIsRows();
    })
  );
}

function wireLiveInputs(runningHeightBefore) {
  document.body.dataset.runningHeight = String(runningHeightBefore);
  ["bsReading", "fsReading"].forEach((id) => {
    document.getElementById(id).addEventListener("input", () => updateLivePreview(runningHeightBefore));
  });
}

function updateLivePreview(runningHeightBefore) {
  const bs = Number(document.getElementById("bsReading").value);
  const fs = Number(document.getElementById("fsReading").value);
  const preview = document.getElementById("livePreview");
  const bsOk = document.getElementById("bsReading").value !== "" && !Number.isNaN(bs);
  const fsOk = document.getElementById("fsReading").value !== "" && !Number.isNaN(fs);

  let html = "";
  if (bsOk && fsOk) {
    const dh = bs - fs;
    const newHeight = runningHeightBefore + dh;
    html = `Δh trạm = ${dh >= 0 ? "+" : ""}${dh.toFixed(4)} m <span class="unit">→ H tương đối điểm cuối: ${newHeight.toFixed(4)} m</span>`;
  } else if (bsOk) {
    const hi = runningHeightBefore + bs;
    html = `HI tương đối = ${hi.toFixed(4)} m <span class="unit">(chưa nhập FS)</span>`;
  } else {
    html = `— <span class="unit">nhập BS và FS để xem chênh cao</span>`;
  }
  preview.innerHTML = html;
}

async function saveStation(lineId, runningHeightBefore) {
  const bsPoint = document.getElementById("bsPoint").value.trim();
  const bsReading = Number(document.getElementById("bsReading").value);
  const fsPoint = document.getElementById("fsPoint").value.trim();
  const fsReading = Number(document.getElementById("fsReading").value);
  const note = document.getElementById("note").value.trim();

  if (!bsPoint || !fsPoint || Number.isNaN(bsReading) || Number.isNaN(fsReading)) {
    toast("Cần nhập đủ điểm + số đọc cho BS và FS.", "danger");
    return;
  }
  const cleanIs = isRows
    .filter((r) => r.point.trim() !== "" && r.readingM !== "")
    .map((r) => ({ point: r.point.trim(), readingM: Number(r.readingM) }));

  const payload = {
    bsPoint,
    bsReadingM: bsReading,
    fsPoint,
    fsReadingM: fsReading,
    isList: cleanIs,
    note,
  };

  if (editingStationId != null) {
    await db.updateStation(editingStationId, payload);
    editingStationId = null;
    toast("Đã cập nhật trạm đo.");
  } else {
    await db.addStation(lineId, payload);
    toast("Đã lưu trạm đo.");
  }
  renderLineDetail(lineId);
}

// ---------------- Màn 5: Xuất dữ liệu ----------------

async function renderExport(projectId) {
  const projects = await db.listProjects();
  const project = projects.find((p) => p.id === projectId);
  if (!project) {
    location.hash = "#/";
    return;
  }
  const lines = await db.listLines(projectId);

  app.innerHTML = `
    ${topbar("Xuất dữ liệu", `/project/${project.id}`)}
    <div class="card">
      <p>Dự án <strong>${esc(project.name)}</strong> — ${lines.length} tuyến đo.</p>
      <p class="empty-hint" style="padding:6px 0">
        Nên xuất file JSON để lưu dự phòng ngay sau mỗi buổi đo — dữ liệu trên
        điện thoại (đặc biệt iOS) có thể bị xoá nếu lâu không mở app.
      </p>
      <div class="export-buttons">
        <button class="btn btn-primary" id="btnExportJson">Xuất JSON (dùng cho chương trình bình sai)</button>
        <button class="btn btn-secondary" id="btnExportCsv">Xuất CSV</button>
      </div>
    </div>
  `;

  document.getElementById("btnExportJson").addEventListener("click", async () => {
    try {
      await exportProjectJson(project);
      toast("Đã xuất file JSON.");
    } catch (err) {
      toast("Lỗi khi xuất file: " + err.message, "danger");
    }
  });
  document.getElementById("btnExportCsv").addEventListener("click", async () => {
    try {
      await exportProjectCsv(project);
      toast("Đã xuất file CSV.");
    } catch (err) {
      toast("Lỗi khi xuất file: " + err.message, "danger");
    }
  });
}
