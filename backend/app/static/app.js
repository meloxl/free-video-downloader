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
const summaryTemplateInput = document.getElementById("summaryTemplate");
const summaryPanel = document.getElementById("summaryPanel");
const summaryPanelTitle = document.getElementById("summaryPanelTitle");
const summaryContent = document.getElementById("summaryContent");
const summaryExportBtn = document.getElementById("summaryExportBtn");
const summaryExportDocxBtn = document.getElementById("summaryExportDocxBtn");
const transcriptExportBtn = document.getElementById("transcriptExportBtn");
const summaryCopyBtn = document.getElementById("summaryCopyBtn");

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

function summaryStatusText(s) {
  if (s === "queued") return "总结排队中";
  if (s === "transcribing") return "字幕提取中";
  if (s === "summarizing") return "AI 总结中";
  if (s === "done") return "总结已完成";
  if (s === "failed") return "总结失败";
  if (s === "skipped") return "未启用总结";
  return "等待总结";
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

  const summaryBtn = el("button", {
    class: "hidden rounded-xl px-3 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50 ring-1 ring-brand-200",
    type: "button",
    onclick: async () => {
      try {
        const res = await fetch(`/api/jobs/${job.id}/summary`);
        if (!res.ok) throw new Error("总结尚未就绪");
        const data = await res.json();
        const s = data.summary_result || {};
        const text = [
          "【视频大纲】",
          ...(s.outline || []).map((x, i) => `${i + 1}. ${x}`),
          "",
          "【核心要点】",
          ...(s.key_points || []).map((x, i) => `${i + 1}. ${x}`),
          "",
          "【行动建议】",
          ...(s.action_items || []).map((x, i) => `${i + 1}. ${x}`),
          "",
          "【关键词术语】",
          ...(s.terms || []).map((x, i) => `${i + 1}. ${x}`),
        ].join("\n");
        if (summaryPanelTitle) summaryPanelTitle.textContent = "AI 总结结果";
        if (summaryContent) summaryContent.textContent = text || "暂无总结内容";
        if (summaryPanel) summaryPanel.classList.remove("hidden");
        if (summaryExportBtn) {
          summaryExportBtn.href = `/api/jobs/${job.id}/summary.md`;
          summaryExportBtn.classList.remove("hidden");
        }
        if (summaryExportDocxBtn) {
          summaryExportDocxBtn.href = `/api/jobs/${job.id}/summary.docx`;
          summaryExportDocxBtn.classList.remove("hidden");
        }
        if (transcriptExportBtn) {
          transcriptExportBtn.classList.add("hidden");
        }
      } catch (e) {
        alert((e && e.message) ? e.message : "读取总结失败");
      }
    },
  }, [el("span", { text: "查看总结" })]);

  const transcriptBtn = el("button", {
    class: "hidden rounded-xl px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 ring-1 ring-indigo-200",
    type: "button",
    onclick: async () => {
      try {
        const res = await fetch(`/api/jobs/${job.id}/transcript`);
        if (!res.ok) throw new Error("字幕尚未就绪");
        const data = await res.json();
        const t = data.transcript || {};
        const text = [
          `【来源】${t.source || "unknown"}`,
          `【语言】${t.lang || "unknown"}`,
          "",
          t.text || "",
        ].join("\n");
        if (summaryPanelTitle) summaryPanelTitle.textContent = "字幕 / 转写内容";
        if (summaryContent) summaryContent.textContent = text || "暂无字幕内容";
        if (summaryPanel) summaryPanel.classList.remove("hidden");
        if (transcriptExportBtn) {
          transcriptExportBtn.href = `/api/jobs/${job.id}/transcript.txt`;
          transcriptExportBtn.classList.remove("hidden");
        }
        if (summaryExportBtn) summaryExportBtn.classList.add("hidden");
        if (summaryExportDocxBtn) summaryExportDocxBtn.classList.add("hidden");
      } catch (e) {
        alert((e && e.message) ? e.message : "读取字幕失败");
      }
    },
  }, [el("span", { text: "查看字幕" })]);

  const summaryState = el("div", { class: "mt-2 text-xs font-semibold text-slate-500", text: summaryStatusText(job.summary_status) });

  const err = el("div", { class: "mt-3 hidden text-xs font-semibold text-rose-600" });
  const transcriptErr = el("div", { class: "mt-1 hidden text-xs font-semibold text-amber-600" });
  const summaryErr = el("div", { class: "mt-1 hidden text-xs font-semibold text-rose-600" });
  btns.appendChild(downloadBtn);
  btns.appendChild(summaryBtn);
  btns.appendChild(transcriptBtn);
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
    summaryState,
    transcriptErr,
    summaryErr,
    err,
    btns,
  ]);

  wrap._progressInner = progressInner;
  wrap._downloadBtn = downloadBtn;
  wrap._summaryBtn = summaryBtn;
  wrap._transcriptBtn = transcriptBtn;
  wrap._summaryState = summaryState;
  wrap._transcriptErr = transcriptErr;
  wrap._summaryErr = summaryErr;
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

  const summaryDone = data.summary_status === "done";
  data._node._summaryBtn.classList.toggle("hidden", !summaryDone);
  data._node._summaryBtn.classList.toggle("inline-flex", summaryDone);
  const transcriptReady = !!data.transcript_available;
  data._node._transcriptBtn.classList.toggle("hidden", !transcriptReady);
  data._node._transcriptBtn.classList.toggle("inline-flex", transcriptReady);
  data._node._summaryState.textContent = summaryStatusText(data.summary_status);

  if (data.status === "failed") {
    data._node._err.textContent = data.error || "下载失败，请换一个链接或稍后重试";
    data._node._err.classList.remove("hidden");
  } else {
    data._node._err.classList.add("hidden");
  }

  if (data.transcript_error) {
    data._node._transcriptErr.textContent = `字幕失败：${data.transcript_error}`;
    data._node._transcriptErr.classList.remove("hidden");
  } else {
    data._node._transcriptErr.classList.add("hidden");
  }
  if (data.summary_error) {
    data._node._summaryErr.textContent = `总结失败：${data.summary_error}`;
    data._node._summaryErr.classList.remove("hidden");
  } else {
    data._node._summaryErr.classList.add("hidden");
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
      } else if (payload.type === "summary") {
        upsert({
          id: jobId,
          summary_status: payload.summary_status,
          summary_error: payload.summary_error,
          transcript_error: payload.transcript_error,
          summary_result: payload.summary_result,
          // 只有在 summary_status 为 done 时 transcript 才真正可用
          transcript_available: payload.summary_status === "done" && !payload.transcript_error,
        });
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

async function createJobs(urls, summaryTemplate) {
  const body = new FormData();
  body.set("urls", urls);
  body.set("summary_template", summaryTemplate || "learning");
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
      const payload = await createJobs(list.join("\n"), summaryTemplateInput?.value || "learning");
      for (const j of payload.jobs || []) {
        upsert({
          id: j.id,
          url: j.url,
          status: j.status,
          progress: j.progress,
          summary_status: j.summary_status,
          summary_error: j.summary_error,
          transcript_error: j.transcript_error,
          transcript_available: j.transcript_available,
          meta: j.meta,
        });
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

if (summaryCopyBtn) {
  summaryCopyBtn.addEventListener("click", async () => {
    const text = summaryContent?.textContent || "";
    if (!text.trim()) return;
    await navigator.clipboard?.writeText(text);
  });
}
