/**
 * Sentinel dashboard client-side behavior.
 *
 * Deliberately framework-free: the dashboard's job is showing a filterable
 * table clearly, which plain DOM APIs handle without the overhead of a
 * build step. Rows are built with textContent (never innerHTML) for any
 * field that originates from an external source, since headlines and
 * summaries are untrusted content collected from third-party feeds.
 */

(function () {
  const scoreSelect = document.getElementById("filter-score");
  const sentimentSelect = document.getElementById("filter-sentiment");
  const categorySelect = document.getElementById("filter-category");
  const tbody = document.getElementById("items-tbody");
  const emptyState = document.getElementById("empty-state");
  const visibleCount = document.getElementById("visible-count");
  const lastScanTime = document.getElementById("last-scan-time");

  function setLastScanTime() {
    const now = new Date();
    lastScanTime.textContent = now.toLocaleString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      month: "short",
      day: "numeric",
    });
  }

  function buildSignalBars(score, sentiment) {
    const wrapper = document.createElement("div");
    wrapper.className = `signal-bars signal-bars--${sentiment.toLowerCase()}`;
    wrapper.title = `Score ${score}/5`;
    for (let i = 1; i <= 5; i++) {
      const bar = document.createElement("span");
      bar.className = "signal-bar" + (i <= score ? " is-filled" : "");
      wrapper.appendChild(bar);
    }
    return wrapper;
  }

  function buildRow(item) {
    const tr = document.createElement("tr");
    tr.className = "item-row";
    tr.dataset.sentiment = item.sentiment;

    const signalTd = document.createElement("td");
    signalTd.className = "col-signal";
    signalTd.appendChild(buildSignalBars(item.score, item.sentiment));
    tr.appendChild(signalTd);

    const sentimentTd = document.createElement("td");
    sentimentTd.className = "col-sentiment";
    const dot = document.createElement("span");
    dot.className = `sentiment-dot sentiment-dot--${item.sentiment.toLowerCase()}`;
    const label = document.createElement("span");
    label.className = "sentiment-label";
    label.textContent = item.sentiment;
    sentimentTd.appendChild(dot);
    sentimentTd.appendChild(label);
    tr.appendChild(sentimentTd);

    const categoryTd = document.createElement("td");
    categoryTd.className = "col-category";
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = item.category;
    categoryTd.appendChild(chip);
    tr.appendChild(categoryTd);

    const headlineTd = document.createElement("td");
    headlineTd.className = "col-headline";
    const link = document.createElement("a");
    link.className = "headline-link";
    link.textContent = item.title;
    if (typeof item.url === "string" && item.url.startsWith("http")) {
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noopener";
    }
    const sourceDiv = document.createElement("div");
    sourceDiv.className = "source-name";
    sourceDiv.textContent = item.source_name;
    const summaryDiv = document.createElement("div");
    summaryDiv.className = "summary-text";
    summaryDiv.textContent = item.summary;
    headlineTd.appendChild(link);
    headlineTd.appendChild(sourceDiv);
    headlineTd.appendChild(summaryDiv);
    tr.appendChild(headlineTd);

    const dateTd = document.createElement("td");
    dateTd.className = "col-date mono";
    dateTd.textContent = (item.published_at || "").slice(0, 10);
    tr.appendChild(dateTd);

    return tr;
  }

  function renderItems(items) {
    tbody.innerHTML = "";
    items.forEach((item) => tbody.appendChild(buildRow(item)));
    visibleCount.textContent = items.length;
    emptyState.style.display = items.length === 0 ? "block" : "none";
  }

  function currentFilters() {
    const params = new URLSearchParams();
    if (scoreSelect.value) params.set("min_score", scoreSelect.value);
    if (sentimentSelect.value) params.set("sentiment", sentimentSelect.value);
    if (categorySelect.value) params.set("category", categorySelect.value);
    return params;
  }

  async function applyFilters() {
    const params = currentFilters();
    try {
      const response = await fetch(`/api/items?${params.toString()}`);
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      const items = await response.json();
      renderItems(items);
    } catch (error) {
      console.error("Failed to load filtered items:", error);
    }
  }

  scoreSelect.addEventListener("change", applyFilters);
  sentimentSelect.addEventListener("change", applyFilters);
  categorySelect.addEventListener("change", applyFilters);

  setLastScanTime();
})();
