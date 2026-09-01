function buildRow({ room, detail, status, statusOptions, statusUrl, cancelUrl }) {
  const row = document.createElement("div");
  row.className = "row";

  const badge = document.createElement("span");
  badge.className = "room-badge";
  badge.textContent = room; // room_number comes from guest input - textContent keeps it as plain text, never HTML

  const detailEl = document.createElement("span");
  detailEl.className = "row-detail";
  detailEl.textContent = detail;

  row.append(badge, detailEl);

  if (statusOptions && statusUrl) {
    // Categories with a real status column get a dropdown of their valid values.
    const select = document.createElement("select");
    select.className = "status-select";

    statusOptions.forEach((option) => {
      const optionEl = document.createElement("option");
      optionEl.value = option;
      optionEl.textContent = option.replace(/_/g, " ");
      if (option === status) optionEl.selected = true;
      select.appendChild(optionEl);
    });

    select.addEventListener("change", async () => {
      select.disabled = true;
      try {
        const response = await fetch(statusUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: select.value }),
        });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        loadDashboard(); // re-fetch so a status that no longer qualifies (e.g. "done") drops off the board
      } catch (error) {
        select.disabled = false;
      }
    });

    row.appendChild(select);
  } else {
    // Wake-up calls have no status column, just a fixed "active" pill.
    const pill = document.createElement("span");
    pill.className = `status-pill status-${status}`;
    pill.textContent = status.replace(/_/g, " ");
    row.appendChild(pill);
  }

  if (cancelUrl) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mark-done";
    button.textContent = "Cancel";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const response = await fetch(cancelUrl, { method: "POST" });
        if (!response.ok) throw new Error(`Request failed: ${response.status}`);
        loadDashboard();
      } catch (error) {
        button.disabled = false;
      }
    });
    row.appendChild(button);
  }

  return row;
}

function renderPanel(panelId, rows, emptyText) {
  const panel = document.getElementById(panelId);
  const list = panel.querySelector(".row-list");
  const count = panel.querySelector(".count");

  list.innerHTML = "";
  count.textContent = rows.length;

  if (rows.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = emptyText;
    list.appendChild(empty);
    return;
  }

  rows.forEach((row) => {
    list.appendChild(buildRow(row));
  });
}

// Each of these turns one category's raw API objects into the plain
// {room, detail, status} shape renderPanel() expects.

const HOUSEKEEPING_STATUSES = ["pending", "in_progress", "done", "cancelled"];
const MAINTENANCE_STATUSES = ["open", "in_progress", "resolved"];
const ORDER_STATUSES = ["received", "preparing", "delivered", "cancelled"];
const ESCALATION_STATUSES = ["open", "resolved"];

function mapHousekeeping(items) {
  return items.map((item) => ({
    room: item.room_number,
    detail: item.notes ? `${item.request_type} — ${item.notes}` : item.request_type,
    status: item.status,
    statusOptions: HOUSEKEEPING_STATUSES,
    statusUrl: `/staff/housekeeping/${item.id}/status`,
  }));
}

function mapMaintenance(items) {
  return items.map((item) => ({
    room: item.room_number,
    detail: item.description,
    status: item.status,
    statusOptions: MAINTENANCE_STATUSES,
    statusUrl: `/staff/maintenance/${item.id}/status`,
  }));
}

function mapOrders(items) {
  return items.map((item) => {
    const orderedItems = JSON.parse(item.items_json);
    const summary = orderedItems.map((i) => `${i.quantity}x ${i.name}`).join(", ");
    return {
      room: item.room_number,
      detail: item.notes ? `${summary} (${item.notes})` : summary,
      status: item.status,
      statusOptions: ORDER_STATUSES,
      statusUrl: `/staff/orders/${item.id}/status`,
    };
  });
}

function mapWakeUpCalls(items) {
  return items.map((item) => ({
    room: item.room_number,
    detail: new Date(item.time).toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
    status: "active",
    cancelUrl: `/staff/wakeup/${item.id}/cancel`,
  }));
}

function mapEscalations(items) {
  return items.map((item) => ({
    room: item.room_number,
    detail: item.reason,
    status: item.status,
    statusOptions: ESCALATION_STATUSES,
    statusUrl: `/staff/escalations/${item.id}/status`,
  }));
}

async function loadDashboard() {
  const response = await fetch("/staff/requests");
  const data = await response.json();

  renderPanel("panel-housekeeping", mapHousekeeping(data.housekeeping), "No open housekeeping requests");
  renderPanel("panel-maintenance", mapMaintenance(data.maintenance), "No open maintenance tickets");
  renderPanel("panel-orders", mapOrders(data.orders), "No open orders");
  renderPanel("panel-wakeup", mapWakeUpCalls(data.wake_up_calls), "No active wake-up calls");
  renderPanel("panel-escalations", mapEscalations(data.escalations), "No open escalations");
}

function showCheckoutStatus(message) {
  const status = document.getElementById("checkout-status");
  status.textContent = message;
  setTimeout(() => {
    status.textContent = "";
  }, 3000);
}

const CATEGORY_LABELS = {
  housekeeping: "housekeeping request",
  maintenance: "maintenance ticket",
  orders: "order",
  wake_up_calls: "wake-up call",
  escalations: "escalation",
};

// Turns {housekeeping: 2, orders: 1, ...} into "2 housekeeping requests, 1 order"
function describeOutstanding(counts) {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .map(([category, count]) => {
      const label = CATEGORY_LABELS[category];
      return `${count} ${label}${count > 1 ? "s" : ""}`;
    })
    .join(", ");
}

async function requestCheckout(room, force) {
  const url = force
    ? `/staff/checkout/${encodeURIComponent(room)}?force=true`
    : `/staff/checkout/${encodeURIComponent(room)}`;

  const response = await fetch(url, { method: "POST" });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function setupCheckoutForm() {
  const form = document.getElementById("checkout-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const input = document.getElementById("checkout-room");
    const room = input.value.trim();
    if (!room) return;

    const button = form.querySelector("button");
    button.disabled = true;

    try {
      let result = await requestCheckout(room, false);

      // The backend refuses the first time if the room still has open work -
      // ask the staff member, then repeat the call with force=true.
      if (result.status === "needs_confirmation") {
        const proceed = confirm(
          `Room ${room} still has ${describeOutstanding(result.counts)}. Check out anyway?`
        );

        if (!proceed) {
          showCheckoutStatus("Checkout cancelled.");
          return;
        }

        result = await requestCheckout(room, true);
      }

      input.value = "";
      showCheckoutStatus(`Room ${room} checked out.`);
      loadDashboard(); // reflect any cancelled housekeeping/orders/wake-up calls immediately
    } catch (error) {
      showCheckoutStatus("Checkout failed - please try again.");
    } finally {
      button.disabled = false;
    }
  });
}

function init() {
  loadDashboard();
  setupCheckoutForm();
}

init();