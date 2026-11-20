let runId = null;

const $ = (id) => document.getElementById(id);

function showStep(id) {
  document.querySelectorAll(".step").forEach((el) => el.classList.add("hidden"));
  $(id).classList.remove("hidden");
}

function showError(message) {
  $("error-message").textContent = message;
  showStep("step-error");
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

$("start-btn").addEventListener("click", async () => {
  const company = $("company").value.trim();
  const subject = $("subject").value.trim();
  if (!company || !subject) return;
  try {
    const data = await api("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company, subject }),
    });
    runId = data.run_id;
    renderEntities(data.candidate_entities);
    showStep("step-entities");
  } catch (e) {
    showError(e.message);
  }
});

function renderEntities(entities) {
  const container = $("entities-list");
  container.innerHTML = "";
  entities.forEach((name, i) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" checked data-entity="${i}"> ${name}`;
    container.appendChild(label);
  });
  container.dataset.entities = JSON.stringify(entities);
}

$("entities-btn").addEventListener("click", async () => {
  const entities = JSON.parse($("entities-list").dataset.entities);
  const checked = [...$("entities-list").querySelectorAll("input[type=checkbox]")]
    .filter((cb) => cb.checked)
    .map((cb) => entities[Number(cb.dataset.entity)]);
  try {
    const data = await api(`/api/runs/${runId}/entities`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved: checked }),
    });
    $("keywords-text").value = data.candidate_keywords.join("\n");
    showStep("step-keywords");
  } catch (e) {
    showError(e.message);
  }
});

$("keywords-btn").addEventListener("click", async () => {
  const approved = $("keywords-text").value.split("\n").map((s) => s.trim()).filter(Boolean);
  try {
    await api(`/api/runs/${runId}/keywords`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    });
    showStep("step-progress");
    listenForEvents();
  } catch (e) {
    showError(e.message);
  }
});

function listenForEvents() {
  const source = new EventSource(`/api/runs/${runId}/events`);
  source.onmessage = (msg) => {
    const event = JSON.parse(msg.data);
    if (event.type === "progress") {
      $("progress-message").textContent = event.message;
      if (event.total) {
        $("progress-bar").max = event.total;
        $("progress-bar").value = event.current;
      } else {
        $("progress-bar").removeAttribute("value");
      }
    } else if (event.type === "categorization_ready") {
      renderCategorization(event.categories, event.patents);
      showStep("step-categorization");
      source.close();
    } else if (event.type === "report_ready") {
      renderDownloads(event.files);
      showStep("step-report");
      source.close();
    } else if (event.type === "error") {
      showError(event.message);
      source.close();
    }
  };
  source.onerror = () => {
    // EventSource auto-retries; nothing to do unless the run itself errored,
    // which arrives as an "error" event above before the connection drops.
  };
}

let categorizationPatents = [];

function renderCategorization(categories, patents) {
  categorizationPatents = patents;
  $("categorization-summary").textContent =
    `${patents.length} relevant patents, ${categories.length} proposed categories: ${categories.join(", ")}`;

  const table = document.createElement("table");
  table.innerHTML = "<tr><th>Patent</th><th>Title</th><th>Categories (comma-separated)</th></tr>";
  patents.forEach((p, i) => {
    const row = document.createElement("tr");
    const number = p.patent_number || p.application_number;
    row.innerHTML = `
      <td>${number}</td>
      <td>${p.title}</td>
      <td><input type="text" data-idx="${i}" value="${p.categories.join(", ")}"></td>
    `;
    table.appendChild(row);
  });
  const container = $("categorization-table");
  container.innerHTML = "";
  container.appendChild(table);
}

$("categorization-btn").addEventListener("click", async () => {
  const categoriesSet = new Set();
  const assignments = {};
  $("categorization-table").querySelectorAll("input[data-idx]").forEach((input) => {
    const patent = categorizationPatents[Number(input.dataset.idx)];
    const cats = input.value.split(",").map((s) => s.trim()).filter(Boolean);
    assignments[patent.application_number] = cats;
    cats.forEach((c) => categoriesSet.add(c));
  });
  try {
    await api(`/api/runs/${runId}/categorization`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ categories: [...categoriesSet], assignments }),
    });
    showStep("step-progress");
    $("progress-message").textContent = "Generating report...";
    $("progress-bar").removeAttribute("value");
    listenForEvents();
  } catch (e) {
    showError(e.message);
  }
});

function renderDownloads(files) {
  const container = $("downloads");
  container.innerHTML = "";
  const labels = { csv: "Download CSV", report_md: "Download Report (Markdown)", report_html: "Download Report (HTML)" };
  Object.keys(files).forEach((kind) => {
    const link = document.createElement("a");
    link.href = `/api/runs/${runId}/download/${kind}`;
    link.textContent = labels[kind];
    link.setAttribute("download", files[kind]);
    container.appendChild(link);
  });
}
