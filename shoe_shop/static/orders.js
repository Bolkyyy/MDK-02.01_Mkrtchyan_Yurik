let user = null;

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
  let order;
  try {
    order = await api("/api/order?id=" + id);
  } catch (e) {
    alert(e.message);
    return;
  }
  let rows = "";
  for (const item of order.items) {
    rows += `<tr><td>${item.product}</td><td>${item.size}</td>` +
      `<td>${item.quantity}</td><td>${item.unit_price}</td><td>${item.sum}</td></tr>`;
  }
  showModal(`<h2>Заказ № ${order.order_num}</h2>
    <p>Дата: ${order.order_date}</p>
    <p>Клиент: ${order.full_name}</p>
    <table>
      <tr><th>Товар</th><th>Размер</th><th>Количество</th><th>Цена</th><th>Сумма</th></tr>
      ${rows}
    </table>
    <p><b>Итого: ${order.total}</b></p>
    <button onclick="closeModal()">Закрыть</button>`);
}

document.getElementById("btn-login").onclick = login;
