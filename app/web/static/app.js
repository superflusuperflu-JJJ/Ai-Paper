const charts = [];

function getRequestedDate() {
  const params = new URLSearchParams(window.location.search);
  return params.get("date") || window.__TODAY__;
}

function escapeHtml(input) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  };
  return String(input || "").replace(/[&<>"']/g, (ch) => map[ch]);
}

function getSummary(p) {
  const s = p.summary_cn || {};
  return {
    one_liner: s.one_liner || "",
    background: s.background || "",
    problem: s.problem || "",
    method: s.method || "",
    effectiveness: s.effectiveness || "",
    highlights: s.highlights || "",
    limitations: s.limitations || "",
    other_info: s.other_info || "",
  };
}

function toPaperMindmapTree(paper) {
  const m = paper.mindmap_cn || {};
  const s = getSummary(paper);
  return {
    name: paper.title || "论文",
    children: [
      { name: `研究核心：${m.research_core || s.problem || ""}` },
      { name: `理论基础：${m.theoretical_basis || "基于既有理论框架进行建模与分析"}` },
      { name: `方法：${m.method || s.method || ""}` },
      { name: `实验成果：${m.experiments || s.effectiveness || ""}` },
      { name: `结论：${m.conclusion || s.one_liner || ""}` },
    ],
  };
}

function renderPaperMindmap(el, paper) {
  const chart = echarts.init(el);
  const tree = toPaperMindmapTree(paper);
  chart.setOption({
    tooltip: { trigger: "item", triggerOn: "mousemove" },
    series: [{
      type: "tree",
      data: [tree],
      top: "3%",
      left: "6%",
      bottom: "3%",
      right: "36%",
      symbolSize: 8,
      expandAndCollapse: true,
      initialTreeDepth: 1,
      animationDurationUpdate: 500,
      lineStyle: { color: "#bcc4d0" },
      itemStyle: { color: "#9aa6b8", borderColor: "#ffffff", borderWidth: 1 },
      label: {
        position: "left",
        verticalAlign: "middle",
        align: "right",
        fontSize: 12,
        color: "#3b4554",
      },
      leaves: {
        label: {
          position: "right",
          align: "left",
          fontSize: 12,
          color: "#394355",
        },
      },
    }],
  });
  charts.push(chart);
}

function renderPapers(runDate, papers) {
  charts.forEach((c) => c.dispose());
  charts.length = 0;

  document.getElementById("current-date").textContent = runDate;
  document.getElementById("panel-title").textContent = `${runDate} 精选论文`;
  document.getElementById("paper-count").textContent = `${papers.length} 篇`;

  const container = document.getElementById("papers-container");
  if (!papers.length) {
    container.innerHTML = '<p class="empty">当前日期还没有可展示的论文结果。可能是任务尚未完成，或本次抓取失败。</p>';
    return;
  }

  container.innerHTML = papers.map((p, idx) => {
    const s = getSummary(p);
    const mapId = `paper-map-${idx}`;
    return `
      <article class="paper-card">
        <h3 class="paper-title"><a href="${escapeHtml(p.url)}" target="_blank" rel="noreferrer">${escapeHtml(p.title)}</a></h3>
        <div class="meta-row">
          <span class="meta-pill">来源 ${escapeHtml(p.source)}</span>
          <span class="meta-pill">分数 ${escapeHtml(p.score)}</span>
          <span class="meta-pill">引用 ${escapeHtml(p.citation_count)}</span>
        </div>

        <div class="summary-grid">
          <section class="summary-item"><span class="summary-label">一句话结论</span><p class="summary-body">${escapeHtml(s.one_liner)}</p></section>
          <section class="summary-item"><span class="summary-label">研究背景</span><p class="summary-body">${escapeHtml(s.background)}</p></section>
          <section class="summary-item"><span class="summary-label">问题定义</span><p class="summary-body">${escapeHtml(s.problem)}</p></section>
          <section class="summary-item"><span class="summary-label">研究方法</span><p class="summary-body">${escapeHtml(s.method)}</p></section>
          <section class="summary-item"><span class="summary-label">效果与结果</span><p class="summary-body">${escapeHtml(s.effectiveness)}</p></section>
          <section class="summary-item"><span class="summary-label">方法亮点</span><p class="summary-body">${escapeHtml(s.highlights)}</p></section>
          <section class="summary-item"><span class="summary-label">局限</span><p class="summary-body">${escapeHtml(s.limitations)}</p></section>
          <section class="summary-item"><span class="summary-label">其他信息</span><p class="summary-body">${escapeHtml(s.other_info)}</p></section>
        </div>

        <p class="selected-reason"><span>入选理由</span>${escapeHtml(p.selected_reason || "")}</p>

        <div class="map-wrap">
          <div class="map-header">研究脉络导图（研究核心 / 理论基础 / 方法 / 实验成果 / 结论）</div>
          <div class="paper-map" id="${mapId}"></div>
        </div>
      </article>
    `;
  }).join("");

  papers.forEach((paper, idx) => {
    const mapEl = document.getElementById(`paper-map-${idx}`);
    if (mapEl) renderPaperMindmap(mapEl, paper);
  });
}

async function loadDay(runDate) {
  const resp = await fetch(`/api/day/${runDate}`);
  if (!resp.ok) return;
  const data = await resp.json();
  renderPapers(runDate, data.papers || []);
  const params = new URLSearchParams(window.location.search);
  if (params.get("date") !== runDate) {
    params.set("date", runDate);
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
  }

  document.querySelectorAll(".day-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.date === runDate);
  });
}

document.querySelectorAll(".day-btn").forEach((btn) => {
  btn.addEventListener("click", () => loadDay(btn.dataset.date));
});

window.addEventListener("resize", () => charts.forEach((c) => c.resize()));
loadDay(getRequestedDate());
