// Lớp bọc IndexedDB thuần (không phụ thuộc thư viện ngoài — cần offline 100%).
// Schema (SPEC.md mục 11.5): projects, points (điểm gốc), lines (tuyến đo),
// stations (trạm máy, mang theo danh sách điểm ngắm giữa isList).

const DB_NAME = "binh_sai_field_db";
const DB_VERSION = 1;

let dbPromise = null;

function openDb() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("projects")) {
        const s = db.createObjectStore("projects", { keyPath: "id", autoIncrement: true });
        s.createIndex("name", "name");
      }
      if (!db.objectStoreNames.contains("points")) {
        const s = db.createObjectStore("points", { keyPath: "id", autoIncrement: true });
        s.createIndex("projectId", "projectId");
      }
      if (!db.objectStoreNames.contains("lines")) {
        const s = db.createObjectStore("lines", { keyPath: "id", autoIncrement: true });
        s.createIndex("projectId", "projectId");
      }
      if (!db.objectStoreNames.contains("stations")) {
        const s = db.createObjectStore("stations", { keyPath: "id", autoIncrement: true });
        s.createIndex("lineId", "lineId");
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

function reqToPromise(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore(storeName, mode, fn) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const store = tx.objectStore(storeName);
    const result = fn(store);
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error);
  });
}

async function add(storeName, obj) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);
    const req = store.add(obj);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function put(storeName, obj) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    const req = tx.objectStore(storeName).put(obj);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function get(storeName, id) {
  const db = await openDb();
  return reqToPromise(db.transaction(storeName, "readonly").objectStore(storeName).get(id));
}

async function getAll(storeName) {
  const db = await openDb();
  return reqToPromise(db.transaction(storeName, "readonly").objectStore(storeName).getAll());
}

async function getAllByIndex(storeName, indexName, value) {
  const db = await openDb();
  return reqToPromise(
    db.transaction(storeName, "readonly").objectStore(storeName).index(indexName).getAll(value)
  );
}

async function remove(storeName, id) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    tx.objectStore(storeName).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// ---- Dự án ----

export async function createProject(name) {
  return add("projects", { name, createdAt: Date.now() });
}

export async function listProjects() {
  const rows = await getAll("projects");
  return rows.sort((a, b) => b.createdAt - a.createdAt);
}

export async function deleteProject(projectId) {
  const [points, lines] = await Promise.all([
    getAllByIndex("points", "projectId", projectId),
    getAllByIndex("lines", "projectId", projectId),
  ]);
  for (const p of points) await remove("points", p.id);
  for (const l of lines) {
    const stations = await getAllByIndex("stations", "lineId", l.id);
    for (const st of stations) await remove("stations", st.id);
    await remove("lines", l.id);
  }
  await remove("projects", projectId);
}

// ---- Điểm gốc ----

export async function createPoint(projectId, name, heightM) {
  return add("points", { projectId, name, heightM, createdAt: Date.now() });
}

export async function listPoints(projectId) {
  const rows = await getAllByIndex("points", "projectId", projectId);
  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

export async function deletePoint(id) {
  return remove("points", id);
}

// ---- Tuyến đo ----

export async function createLine(projectId, name, fromPoint, toPoint) {
  return add("lines", { projectId, name, fromPoint, toPoint, note: "", createdAt: Date.now(), closedManually: false });
}

export async function listLines(projectId) {
  const rows = await getAllByIndex("lines", "projectId", projectId);
  return rows.sort((a, b) => b.createdAt - a.createdAt);
}

export async function getLine(id) {
  return get("lines", id);
}

export async function updateLine(id, patch) {
  const line = await get("lines", id);
  if (!line) throw new Error("Không tìm thấy tuyến id=" + id);
  return put("lines", { ...line, ...patch });
}

export async function deleteLine(id) {
  const stations = await getAllByIndex("stations", "lineId", id);
  for (const st of stations) await remove("stations", st.id);
  return remove("lines", id);
}

// ---- Trạm đo ----

export async function addStation(lineId, station) {
  const existing = await getAllByIndex("stations", "lineId", lineId);
  const orderIndex = existing.length ? Math.max(...existing.map((s) => s.orderIndex)) + 1 : 1;
  return add("stations", {
    lineId,
    orderIndex,
    bsPoint: station.bsPoint,
    bsReadingMm: station.bsReadingMm,
    fsPoint: station.fsPoint,
    fsReadingMm: station.fsReadingMm,
    isList: station.isList || [],
    note: station.note || "",
    createdAt: Date.now(),
  });
}

export async function listStations(lineId) {
  const rows = await getAllByIndex("stations", "lineId", lineId);
  return rows.sort((a, b) => a.orderIndex - b.orderIndex);
}

export async function updateStation(id, patch) {
  const st = await get("stations", id);
  if (!st) throw new Error("Không tìm thấy trạm id=" + id);
  return put("stations", { ...st, ...patch });
}

export async function deleteStation(id) {
  return remove("stations", id);
}

// ---- Tổng hợp tuyến ----

export function stationDhM(station) {
  return (station.bsReadingMm - station.fsReadingMm) / 1000;
}

export async function lineSummary(lineId) {
  const line = await get("lines", lineId);
  const stations = await listStations(lineId);
  const totalDhM = stations.reduce((sum, s) => sum + stationDhM(s), 0);
  const totalStations = stations.length;
  const closed = !!line && !!line.fromPoint && line.fromPoint === line.toPoint;
  return { line, stations, totalDhM, totalStations, closed };
}
