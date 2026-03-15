const state = {
  cart: [],
  orders: [],
  notificationsIntervalId: null,
};

const statusClassMap = {
  placed: "placed",
  pending: "pending",
  preparing: "preparing",
  ready: "ready",
  delivered: "delivered",
  queued: "queued",
  cooking: "cooking",
  done: "done",
  available: "available",
  unavailable: "unavailable",
};

document.addEventListener("DOMContentLoaded", async () => {
  bindTabs();
  bindActions();
  await Promise.all([
    loadMenu(),
    loadOrders(),
    loadKitchenQueue(),
    loadNotifications(),
  ]);
  startNotificationPolling();
  renderCart();
});

function bindTabs() {
  const buttons = document.querySelectorAll(".tab-button");
  const panels = document.querySelectorAll(".tab-panel");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      buttons.forEach((item) => item.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`[data-panel="${button.dataset.tab}"]`).classList.add("active");
    });
  });
}

function bindActions() {
  document.getElementById("refresh-menu").addEventListener("click", loadMenu);
  document.getElementById("refresh-orders").addEventListener("click", loadOrders);
  document.getElementById("refresh-kitchen").addEventListener("click", loadKitchenQueue);
  document
    .getElementById("refresh-notifications")
    .addEventListener("click", loadNotifications);
  document.getElementById("place-order").addEventListener("click", placeOrder);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch (error) {
      message = `${message}`;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function loadMenu() {
  try {
    const items = await api("/menu");
    const menuGrid = document.getElementById("menu-grid");

    menuGrid.innerHTML = "";
    if (items.length === 0) {
      menuGrid.innerHTML = `<div class="card"><p class="muted">No menu items found.</p></div>`;
      return;
    }

    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "menu-card card";
      card.innerHTML = `
        <span class="badge ${item.available ? "available" : "unavailable"}">
          ${item.available ? "Available" : "Unavailable"}
        </span>
        <h3>${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.description)}</p>
        <div class="menu-footer">
          <span class="price">$${item.price.toFixed(2)}</span>
          <button class="primary-button" ${item.available ? "" : "disabled"}>Add to Order</button>
        </div>
      `;

      card.querySelector("button").addEventListener("click", () => addToCart(item));
      menuGrid.appendChild(card);
    });
  } catch (error) {
    showMessage(error.message, true);
  }
}

function addToCart(item) {
  const existing = state.cart.find((entry) => entry.menu_item_id === item.id);
  if (existing) {
    existing.quantity += 1;
  } else {
    state.cart.push({
      menu_item_id: item.id,
      name: item.name,
      price: item.price,
      quantity: 1,
    });
  }
  renderCart();
  showMessage(`${item.name} added to cart.`);
}

function renderCart() {
  const cartItems = document.getElementById("cart-items");
  const cartSummary = document.getElementById("cart-summary");
  const total = state.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const count = state.cart.reduce((sum, item) => sum + item.quantity, 0);

  document.getElementById("cart-total-hero").textContent = `$${total.toFixed(2)}`;
  document.getElementById("cart-count-hero").textContent = `${count} item${count === 1 ? "" : "s"} selected`;

  if (state.cart.length === 0) {
    cartItems.innerHTML = `<p class="muted">Your cart is empty.</p>`;
    cartSummary.textContent = "No items selected.";
    return;
  }

  cartItems.innerHTML = "";
  state.cart.forEach((item) => {
    const row = document.createElement("div");
    row.className = "cart-item";
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <div class="muted">$${item.price.toFixed(2)} each</div>
      </div>
      <div class="quantity-controls">
        <button class="quantity-button" data-action="decrement">-</button>
        <span>${item.quantity}</span>
        <button class="quantity-button" data-action="increment">+</button>
        <button class="ghost-button" data-action="remove">Remove</button>
      </div>
    `;

    row.querySelector('[data-action="increment"]').addEventListener("click", () => {
      item.quantity += 1;
      renderCart();
    });
    row.querySelector('[data-action="decrement"]').addEventListener("click", () => {
      if (item.quantity > 1) {
        item.quantity -= 1;
      } else {
        state.cart = state.cart.filter((entry) => entry.menu_item_id !== item.menu_item_id);
      }
      renderCart();
    });
    row.querySelector('[data-action="remove"]').addEventListener("click", () => {
      state.cart = state.cart.filter((entry) => entry.menu_item_id !== item.menu_item_id);
      renderCart();
    });

    cartItems.appendChild(row);
  });

  cartSummary.textContent = `${count} item${count === 1 ? "" : "s"} · Total $${total.toFixed(2)}`;
}

async function placeOrder() {
  if (state.cart.length === 0) {
    showMessage("Add at least one pizza before placing an order.", true);
    return;
  }

  const button = document.getElementById("place-order");
  button.disabled = true;
  button.textContent = "Placing...";

  try {
    const payload = {
      items: state.cart.map((item) => ({
        menu_item_id: item.menu_item_id,
        quantity: item.quantity,
      })),
    };
    const order = await api("/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.cart = [];
    renderCart();
    showMessage(`Order #${order.id} placed successfully.`);
    await Promise.all([loadOrders(), loadKitchenQueue(), loadNotifications()]);
    await showOrderDetail(order.id);
    activateTab("orders");
  } catch (error) {
    showMessage(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "Place Order";
  }
}

async function loadOrders() {
  try {
    state.orders = await api("/orders");
    const tbody = document.getElementById("orders-table-body");
    tbody.innerHTML = "";

    if (state.orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="muted">No orders yet.</td></tr>`;
      return;
    }

    state.orders.forEach((order) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>#${order.id}</td>
        <td><span class="badge ${statusClass(order.status)}">${escapeHtml(order.status)}</span></td>
        <td>$${order.total.toFixed(2)}</td>
        <td>${formatDate(order.created_at)}</td>
      `;
      row.addEventListener("click", () => showOrderDetail(order.id));
      tbody.appendChild(row);
    });
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function showOrderDetail(orderId) {
  try {
    const order = await api(`/orders/${orderId}`);
    const detail = document.getElementById("order-detail");
    detail.classList.remove("hidden");
    detail.innerHTML = `
      <h3>Order #${order.id}</h3>
      <p>
        <span class="badge ${statusClass(order.status)}">${escapeHtml(order.status)}</span>
        <span class="muted">Placed ${formatDate(order.created_at)}</span>
      </p>
      <div class="stack">
        ${order.items
          .map(
            (item) => `
              <div class="order-detail-item">
                <strong>${escapeHtml(item.name)}</strong>
                <div class="muted">
                  Qty ${item.quantity} · $${item.unit_price.toFixed(2)} each · Line total $${item.line_total.toFixed(2)}
                </div>
              </div>
            `,
          )
          .join("")}
      </div>
      <p><strong>Total:</strong> $${order.total.toFixed(2)}</p>
    `;
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function loadKitchenQueue() {
  try {
    const queue = await api("/kitchen/queue");
    const container = document.getElementById("kitchen-queue");
    container.innerHTML = "";

    if (queue.length === 0) {
      container.innerHTML = `<div class="card"><p class="muted">Kitchen queue is empty.</p></div>`;
      return;
    }

    queue.forEach((entry) => {
      const item = document.createElement("div");
      item.className = "queue-item";
      const disabled = entry.status !== "queued" ? "disabled" : "";
      item.innerHTML = `
        <div>
          <strong>Order #${entry.order_id}</strong>
          <div class="muted">Started: ${formatMaybeDate(entry.started_at)} · Done: ${formatMaybeDate(entry.done_at)}</div>
        </div>
        <div class="quantity-controls">
          <span class="badge ${statusClass(entry.status)}">${escapeHtml(entry.status)}</span>
          <button class="cook-button" ${disabled}>Start Cooking</button>
        </div>
      `;

      const button = item.querySelector("button");
      button.addEventListener("click", async () => {
        button.disabled = true;
        button.textContent = "Cooking...";
        try {
          await api(`/kitchen/cook/${entry.order_id}`, { method: "POST" });
          showMessage(`Order #${entry.order_id} finished cooking.`);
          await Promise.all([loadKitchenQueue(), loadOrders(), loadNotifications()]);
        } catch (error) {
          showMessage(error.message, true);
        } finally {
          button.textContent = "Start Cooking";
        }
      });

      container.appendChild(item);
    });
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function loadNotifications() {
  try {
    const notifications = await api("/notifications");
    const feed = document.getElementById("notifications-feed");
    feed.innerHTML = "";

    if (notifications.length === 0) {
      feed.innerHTML = `<div class="card"><p class="muted">No notifications yet.</p></div>`;
      return;
    }

    notifications.forEach((notification) => {
      const item = document.createElement("div");
      item.className = "notification-item";
      item.innerHTML = `
        <time>${formatDate(notification.created_at)}</time>
        <strong>Order #${notification.order_id}</strong>
        <div>${escapeHtml(notification.message)}</div>
      `;
      feed.appendChild(item);
    });
  } catch (error) {
    showMessage(error.message, true);
  }
}

function startNotificationPolling() {
  if (state.notificationsIntervalId) {
    clearInterval(state.notificationsIntervalId);
  }
  state.notificationsIntervalId = window.setInterval(loadNotifications, 3000);
}

function activateTab(name) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === name);
  });
}

function showMessage(message, isError = false) {
  const banner = document.getElementById("message-banner");
  banner.textContent = message;
  banner.classList.remove("hidden", "error");
  if (isError) {
    banner.classList.add("error");
  }

  clearTimeout(showMessage.timeoutId);
  showMessage.timeoutId = window.setTimeout(() => {
    banner.classList.add("hidden");
  }, 3500);
}

function formatDate(value) {
  return new Date(value).toLocaleString();
}

function formatMaybeDate(value) {
  return value ? formatDate(value) : "Not yet";
}

function statusClass(status) {
  return statusClassMap[status] || "delivered";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
