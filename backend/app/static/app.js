function el(tag, attrs = {}, children = []) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const c of children) n.appendChild(c);
  return n;
}

const jobGrid = document.getElementById("jobGrid");
const emptyState = document.getElementById("emptyState");
const jobForm = document.getElementById("jobForm");
const urlsInput = document.getElementById("urls");

const jobs = new Map();

function setEmptyState() {
  if (!emptyState) return;
  emptyState.style.display = jobs.size === 0 ? "block" : "none";
}

function formatPct(p) {
  if (p == null || Number.isNaN(p)) return "—";
  const v = Math.max(0, Math.min(100, p));
  return `${v.toFixed(1)}%`;
}

function card(job) {
  const accent = job.status === "finished" ? "bg-emerald-500" : job.status === "failed" ? "bg-rose-500" : "bg-brand-500";
  const statusText =
    job.status === "queued" ? "排队中" :
    job.status === "downloading" ? "下载中" :
    job.status === "finished" ? "已完成" :
    job.status === "failed" ? "失败" :
    job.status === "expired" ? "已过期" :
    job.status;

  const pct = job.progress?.percent;
  const title = (job.display_name || job.progress?.filename || job.url || "任务").toString();

  const badge = el("span", { class: `inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-extrabold text-white ${accent}` }, [
    el("span", { class: "h-1.5 w-1.5 rounded-full bg-white/90" }),
    el("span", { text: statusText }),
  ]);

  const progressOuter = el("div", { class: "mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100 ring-1 ring-slate-200" });
  const progressInner = el("div", { class: `h-full ${accent}`, style: `width:${pct ?? 0}%` });
  progressOuter.appendChild(progressInner);

  const metaLine = el("div", { class: "mt-3 flex items-center justify-between text-xs font-semibold text-slate-500" }, [
    el("div", { text: formatPct(pct) }),
    el("div", { text: job.progress?.speed || "" }),
  ]);

  const btns = el("div", { class: "mt-5 flex items-center gap-2" });
  const downloadBtn = el("a", {
    class: "hidden flex-1 items-center justify-center rounded-xl bg-slate-900 px-3 py-2 text-sm font-extrabold text-white hover:bg-slate-800",
    href: `/api/jobs/${job.id}/file`,
  }, [el("span", { text: "保存到本地" })]);

  const detailBtn = el("button", {
    class: "rounded-xl px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 ring-1 ring-slate-200",
    type: "button",
    onclick: () => navigator.clipboard?.writeText(job.url || ""),
  }, [el("span", { text: "复制链接" })]);

  const err = el("div", { class: "mt-3 hidden text-xs font-semibold text-rose-600" });
  btns.appendChild(downloadBtn);
  btns.appendChild(detailBtn);

  const wrap = el("div", { class: "group rounded-3xl bg-white p-5 shadow-soft ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-lift" }, [
    el("div", { class: "flex items-start justify-between gap-3" }, [
      el("div", { class: "min-w-0" }, [
        el("div", { class: "line-clamp-2 text-sm font-extrabold text-ink-950" , text: title }),
        el("div", { class: "mt-1 line-clamp-1 text-xs font-semibold text-slate-500", text: job.url || "" }),
      ]),
      badge,
    ]),
    progressOuter,
    metaLine,
    err,
    btns,
  ]);

  wrap._progressInner = progressInner;
  wrap._downloadBtn = downloadBtn;
  wrap._err = err;
  return wrap;
}

function upsert(job) {
  const existing = jobs.get(job.id);
  jobs.set(job.id, { ...(existing || {}), ...job });

  const data = jobs.get(job.id);
  if (!data._node) {
    data._node = card(data);
    jobGrid?.prepend(data._node);
  }

  // refresh minimal fields
  const pct = data.progress?.percent;
  const accent = data.status === "finished" ? "bg-emerald-500" : data.status === "failed" ? "bg-rose-500" : "bg-brand-500";
  data._node._progressInner.className = `h-full ${accent}`;
  data._node._progressInner.style.width = `${pct ?? 0}%`;

  const downloadVisible = data.status === "finished";
  data._node._downloadBtn.classList.toggle("hidden", !downloadVisible);
  data._node._downloadBtn.classList.toggle("inline-flex", downloadVisible);

  if (data.status === "failed") {
    data._node._err.textContent = data.error || "下载失败，请换一个链接或稍后重试";
    data._node._err.classList.remove("hidden");
  } else {
    data._node._err.classList.add("hidden");
  }

  setEmptyState();
}

function subscribe(jobId) {
  const es = new EventSource(`/api/jobs/${jobId}/events`);
  es.onmessage = (evt) => {
    try {
      const payload = JSON.parse(evt.data);
      if (payload.type === "progress") {
        upsert({ id: jobId, progress: payload.progress, status: payload.progress.status });
      } else if (payload.type === "status") {
        upsert({ id: jobId, status: payload.status, error: payload.error, display_name: payload.display_name });
      }
    } catch (e) {}
  };
  es.onerror = () => {
    es.close();
    // UI can be refreshed by creating new jobs; keep quiet.
  };
  const data = jobs.get(jobId) || { id: jobId };
  data._es = es;
  jobs.set(jobId, data);
}

async function createJobs(urls) {
  const body = new FormData();
  body.set("urls", urls);
  const res = await fetch("/api/jobs", { method: "POST", body });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || "create job failed");
  }
  return await res.json();
}

function normalizeUrls(raw) {
  return raw
    .split(/\n|\r|\s+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((s) => s.startsWith("http://") || s.startsWith("https://"));
}

if (jobForm) {
  jobForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = urlsInput.value || "";
    const list = normalizeUrls(raw);
    if (list.length === 0) return;

    try {
      const payload = await createJobs(list.join("\n"));
      for (const j of payload.jobs || []) {
        upsert({ id: j.id, url: j.url, status: j.status, progress: j.progress });
        subscribe(j.id);
      }
      urlsInput.value = "";
    } catch (err) {
      alert((err && err.message) ? err.message : "提交失败");
    }
  });
}

function clearFinished() {
  for (const [id, job] of jobs.entries()) {
    if (job.status === "finished" || job.status === "failed" || job.status === "expired") {
      job._es?.close?.();
      job._node?.remove?.();
      jobs.delete(id);
    }
  }
  setEmptyState();
}

window.clearFinished = clearFinished;
setEmptyState();

