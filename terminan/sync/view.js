/* No transport binding until source-bound endpoint and auth ACK. */
(function () {
  "use strict";
  const tabs = [
    "Overview",
    "Infrastructure",
    "Historical Data",
    "Live Market Data",
    "Instruments",
    "Data Integrity",
    "Nodes",
    "Schedules",
    "Resource Usage",
    "Replication",
    "Research",
    "Paper Trading",
    "Logs",
    "Administration",
  ];
  const names = [
    "Byte integrity",
    "Source completeness",
    "Redundancy",
    "Authority freshness",
  ];
  const descriptions = [
    "Content hashes · Segment verification",
    "Expected intervals · Explicit gaps",
    "Verified replicas · Restore readiness",
    "Generation · Revision · Evidence age",
  ];
  const ids = (t) => t.toLowerCase().replaceAll(" ", "-");
  const tablist = document.querySelector("#tabs");
  let selected = 0;
  function select(i) {
    selected = (i + tabs.length) % tabs.length;
    [...tablist.children].forEach((b, n) => {
      b.setAttribute("aria-selected", String(n === selected));
      b.tabIndex = n === selected ? 0 : -1;
    });
    document.querySelector("#page-title").textContent = tabs[selected];
    document.querySelector("#projection-title").textContent =
      tabs[selected] === "Overview" ? "Cluster resources" : tabs[selected];
    document
      .querySelector("#panel")
      .setAttribute("aria-labelledby", "tab-" + ids(tabs[selected]));
  }
  tabs.forEach((name, i) => {
    const b = document.createElement("button");
    b.id = "tab-" + ids(name);
    b.type = "button";
    b.role = "tab";
    b.textContent = name;
    b.setAttribute("aria-controls", "panel");
    b.addEventListener("click", () => select(i));
    b.addEventListener("keydown", (e) => {
      let next;
      if (e.key === "ArrowDown" || e.key === "ArrowRight") next = selected + 1;
      if (e.key === "ArrowUp" || e.key === "ArrowLeft") next = selected - 1;
      if (e.key === "Home") next = 0;
      if (e.key === "End") next = tabs.length - 1;
      if (next !== undefined) {
        e.preventDefault();
        select(next);
        tablist.children[selected].focus();
      }
    });
    tablist.append(b);
  });
  select(0);
  const cards = document.querySelector("#dimensions");
  names.forEach((name, i) => {
    const card = document.createElement("article");
    card.className = "dimension";
    card.dataset.dimension = String(i);
    const number = document.createElement("span");
    number.className = "dimension-index";
    number.textContent = "0" + (i + 1);
    const title = document.createElement("h3");
    title.textContent = name;
    const status = document.createElement("div");
    status.className = "dimension-state";
    status.textContent = "UNKNOWN";
    const note = document.createElement("p");
    note.textContent = descriptions[i];
    card.append(number, title, status, note);
    cards.append(card);
  });
  function render(state, { synthetic = false } = {}) {
    document.querySelector("#qualification").textContent = synthetic
      ? "SYNTHETIC CONTRACT FIXTURE · NOT RUNTIME"
      : "CONTROL API INTEGRATION PENDING";
    document.querySelector("#connection-status").textContent = state.status;
    document.querySelector("#generation").textContent = state.generation || "—";
    document.querySelector("#revision").textContent =
      state.revision === null ? "—" : String(state.revision);
    document.querySelector("#authority").textContent =
      state.authority || "UNKNOWN";
    document.querySelector("#observed").textContent =
      state.lastContact === null
        ? "Never"
        : synthetic
          ? "Synthetic observation"
          : "Awaiting endpoint ACK";
    const rows = [...state.resources.values()];
    const integrity = rows.find((x) => x.resource_type === "integrity");
    const values = TerminanSync.integrityDimensions(
      integrity ? integrity.value : {},
    );
    [...cards.children].forEach((card, i) => {
      const v = values[i];
      let text = typeof v.state === "string" ? v.state : "UNKNOWN";
      if (integrity && integrity.value.committed === false)
        text = "UNCOMMITTED";
      else if (state.status !== "LIVE" && text !== "UNKNOWN")
        text += " · " + state.status;
      card.querySelector(".dimension-state").textContent = text;
    });
    const body = document.querySelector("#resource-rows");
    body.replaceChildren();
    if (!rows.length) {
      const tr = document.createElement("tr"),
        td = document.createElement("td");
      td.colSpan = 4;
      td.className = "empty";
      const symbol = document.createElement("div");
      symbol.className = "empty-symbol";
      symbol.setAttribute("aria-hidden", "true");
      symbol.textContent = "◇";
      const title = document.createElement("strong");
      title.textContent = "Waiting for an authenticated source";
      const info = document.createElement("p");
      info.textContent = "No cluster state has been confirmed.";
      td.append(symbol, title, info);
      tr.append(td);
      body.append(tr);
    } else
      for (const r of rows.slice(0, 200)) {
        const tr = document.createElement("tr");
        for (const text of [
          r.resource_id,
          r.resource_type,
          String(r.resource_revision ?? "—"),
          synthetic ? "Synthetic fixture" : "Source ACK pending",
        ]) {
          const td = document.createElement("td");
          td.textContent = text;
          tr.append(td);
        }
        body.append(tr);
      }
  }
  const client = new TerminanSyncClient.SyncClient({
    onChange: (state) => render(state),
  });
  client.start();
  const timer = setInterval(() => client.tick(), 1000);
  addEventListener(
    "pagehide",
    () => {
      clearInterval(timer);
      client.stop();
    },
    { once: true },
  );
  window.TerminanSyncView = { render };
})();
