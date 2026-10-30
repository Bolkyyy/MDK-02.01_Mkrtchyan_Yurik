let user = null;
let currentOrder = null;
let removedItems = [];

async function api(url, body) {
  const options = { headers: {} };
  if (user) {
    options.headers["X-User-Login"] = encodeURIComponent(user.login);
  }
  if (body !== undefined) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error);
  }
  return data;
}

function showModal(html) {
  document.getElementById("modal-box").innerHTML = html;
  document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal").classList.add("hidden");
}

async function login() {
  const login = document.getElementById("login").value.trim();
  try {
    const data = await api("/api/login?login=" + encodeURIComponent(login));
    user = { id: data.id, full_name: data.full_name, role: data.role, login: login };
  } catch (e) {
    alert(e.message);
    return;
  }
  document.getElementById("user").textContent = user.full_name + " (" + user.role + ")";
  if (user.role !== "Менеджер" && user.role !== "Администратор") {
    document.getElementById("panel").classList.add("hidden");
    alert("Панель заказов доступна только Менеджеру и Администратору");
    return;
  }
  document.getElementById("panel").classList.remove("hidden");
  loadOrders();
}

async function loadOrders() {
  let orders;
  try {
    orders = await api("/api/orders");
  } catch (e) {
    alert(e.message);
    return;
  }
  let html = "<tr><th>№</th><th>Дата</th><th>ФИО</th><th></th></tr>";
  for (const order of orders) {
    html += `<tr><td>${order.order_num}</td><td>${order.order_date}</td><td>${order.full_name}</td>` +
      `<td><button onclick="openOrder(${order.id})">Открыть</button></td></tr>`;
  }
  document.getElementById("orders").innerHTML = html;
}

async function openOrder(id) {
  try {
    currentOrder = await api("/api/order?id=" + id);
  } catch (e) {
    alert(e.message);
    return;
  }
  removedItems = [];
  const admin = user.role === "Администратор";
  let rows = "";
  for (const item of currentOrder.items) {
    rows += `<tr id="item-${item.id}"><td>${item.product}</td><td>${item.size}</td>` +
      `<td>${item.quantity}</td><td>${item.unit_price}</td><td>${item.sum}</td>`;
    if (admin) {
      rows += `<td><button onclick="removeItem(${item.id})">Удалить</button></td>`;
    }
    rows += "</tr>";
  }
  let date = currentOrder.order_date;
  let buttons = `<button onclick="closeModal()">Закрыть</button>`;
  if (admin) {
    date = `<input type="date" id="order-date" value="${currentOrder.order_date}">`;
    buttons = `<button onclick="saveOrder()">Сохранить изменения</button> ` + buttons;
  }
  showModal(`<h2>Заказ № ${currentOrder.order_num}</h2>
    <p>Дата: ${date}</p>
    <p>Клиент: ${currentOrder.full_name}</p>
    <table>
      <tr><th>Товар</th><th>Размер</th><th>Количество</th><th>Цена</th><th>Сумма</th>${admin ? "<th></th>" : ""}</tr>
      ${rows}
    </table>
    <p><b>Итого: ${currentOrder.total}</b></p>
    ${buttons}`);
}

function removeItem(itemId) {
  const row = document.getElementById("item-" + itemId);
  if (removedItems.includes(itemId)) {
    removedItems = removedItems.filter((id) => id !== itemId);
    row.classList.remove("removed");
  } else {
    removedItems.push(itemId);
    row.classList.add("removed");
  }
}

async function saveOrder() {
  const body = {
    id: currentOrder.id,
    order_date: document.getElementById("order-date").value,
    delete_items: removedItems,
  };
  try {
    await api("/api/order/update", body);
  } catch (e) {
    alert(e.message);
    return;
  }
  closeModal();
  alert("Изменения сохранены");
  loadOrders();
}

async function showAddForm() {
  let users;
  try {
    users = await api("/api/users");
  } catch (e) {
    alert(e.message);
    return;
  }
  let options = "";
  for (const u of users) {
    options += `<option value="${u.id}">${u.full_name}</option>`;
  }
  showModal(`<h2>Новый заказ</h2>
    <p>Клиент: <select id="new-user">${options}</select></p>
    <p>Поиск товара: <input id="new-search"> <button onclick="searchProducts()">Найти</button></p>
    <p>Товар: <select id="new-product" onchange="loadSizes()"></select></p>
    <p>Размер: <select id="new-size"></select></p>
    <p>Количество: <input id="new-quantity" type="number" min="1" value="1"></p>
    <button onclick="createOrder()">Сохранить заказ</button>
    <button onclick="closeModal()">Отмена</button>`);
  searchProducts();
}

async function searchProducts() {
  const text = document.getElementById("new-search").value.trim();
  let products;
  try {
    products = await api("/api/products?search=" + encodeURIComponent(text));
  } catch (e) {
    alert(e.message);
    return;
  }
  let options = "";
  for (const p of products) {
    options += `<option value="${p.id}">${p.name} (${p.manufacturer})</option>`;
  }
  document.getElementById("new-product").innerHTML = options;
  loadSizes();
}

async function loadSizes() {
  const productId = document.getElementById("new-product").value;
  let options = "";
  if (productId) {
    try {
      const product = await api("/api/product?id=" + productId);
      for (const s of product.sizes) {
        options += `<option value="${s.size_id}">${s.size} (в наличии ${s.quantity})</option>`;
      }
    } catch (e) {
      alert(e.message);
    }
  }
  document.getElementById("new-size").innerHTML = options;
}

async function createOrder() {
  const productId = Number(document.getElementById("new-product").value);
  const sizeId = Number(document.getElementById("new-size").value);
  const quantity = Number(document.getElementById("new-quantity").value);
  if (!productId || !sizeId) {
    alert("Выберите товар и размер");
    return;
  }
  if (!Number.isInteger(quantity) || quantity < 1) {
    alert("Количество должно быть целым числом больше нуля");
    return;
  }
  const body = {
    user_id: Number(document.getElementById("new-user").value),
    items: [{ product_id: productId, size_id: sizeId, quantity: quantity }],
  };
  let order;
  try {
    order = await api("/api/order/create", body);
  } catch (e) {
    alert(e.message);
    return;
  }
  closeModal();
  alert("Заказ № " + order.order_num + " создан");
  loadOrders();
}

document.getElementById("btn-login").onclick = login;
document.getElementById("btn-add").onclick = showAddForm;
