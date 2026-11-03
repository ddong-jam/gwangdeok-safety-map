// 신고 저장소. 지금은 브라우저 localStorage 에 저장한다.
// 나중에 서버(Supabase, Firebase, GitHub Issues API 등)로 옮길 때는
// 이 파일의 list / add / update / remove 네 함수만 바꾸면 된다.

const KEY = "kd-safety-reports-v1";
const listeners = new Set();

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

let reports = load();

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(reports));
  } catch (e) {
    // 사진이 많아 용량(약 5MB)을 넘으면 저장 실패
    alert("브라우저 저장 공간이 부족합니다. 오래된 신고나 사진을 정리해 주세요.");
    throw e;
  }
  listeners.forEach((fn) => fn(reports));
}

export const store = {
  list: () => reports,
  get: (id) => reports.find((r) => r.id === id),
  add(report) {
    const r = {
      id: (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()) + Math.random().toString(16).slice(2),
      createdAt: new Date().toISOString(),
      status: "new",
      ...report,
    };
    reports = [r, ...reports];
    save();
    return r;
  },
  update(id, patch) {
    reports = reports.map((r) => (r.id === id ? { ...r, ...patch, updatedAt: new Date().toISOString() } : r));
    save();
  },
  remove(id) {
    reports = reports.filter((r) => r.id !== id);
    save();
  },
  replaceAll(list) {
    reports = list;
    save();
  },
  subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
