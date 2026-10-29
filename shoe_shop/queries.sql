-- 1. Все товары дороже 10 000 рублей
SELECT p.id, p.name, m.name AS manufacturer, p.price
FROM Products p
JOIN Manufacturers m ON m.id = p.manufacturer_id
WHERE p.price > 10000
ORDER BY p.price DESC;

-- 2. Товары категории женская обувь
SELECT p.id, p.name, m.name AS manufacturer, p.price
FROM Products p
JOIN Categories c    ON c.id = p.category_id
JOIN Manufacturers m ON m.id = p.manufacturer_id
WHERE c.name = 'Женская обувь'
ORDER BY p.name;

-- 3. Кол-во моделей у каждого производителя
SELECT m.name AS manufacturer, COUNT(p.id) AS models
FROM Manufacturers m
LEFT JOIN Products p ON p.manufacturer_id = m.id
GROUP BY m.id
ORDER BY models DESC, manufacturer;

-- 4. Средняя цена по категориям
SELECT c.name AS category, COUNT(p.id) AS models, ROUND(AVG(p.price), 2) AS avg_price
FROM Categories c
JOIN Products p ON p.category_id = c.id
GROUP BY c.id
ORDER BY avg_price DESC;

-- 5. Товары, которых на складе меньше 3 (суммарно)
SELECT p.id, p.name, COALESCE(SUM(s.quantity), 0) AS total_qty
FROM Products p
LEFT JOIN Stock s ON s.product_id = p.id
GROUP BY p.id
HAVING total_qty < 3
ORDER BY total_qty, p.name;

-- 6. Товары без заказов за прошлый месяц (получат скидку 25%)
SELECT p.id, p.name, p.price, ROUND(p.price * 0.75, 2) AS price_with_discount
FROM Products p
WHERE p.id NOT IN (
    SELECT oi.product_id
    FROM OrderItems oi
    JOIN Orders o ON o.id = oi.order_id
    WHERE o.order_date >= date('now', 'start of month', '-1 month')
      AND o.order_date <  date('now', 'start of month')
)
ORDER BY p.id;

-- 7. Топ-5 самых дорогих заказов с ФИО клиента
SELECT o.order_num, o.order_date, u.full_name,
       SUM(oi.quantity * oi.unit_price) AS order_total
FROM Orders o
JOIN Users u       ON u.id = o.user_id
JOIN OrderItems oi ON oi.order_id = o.id
GROUP BY o.id
ORDER BY order_total DESC
LIMIT 5;

-- 8. Список всех размеров, которые есть на складе, но не заказывались.
SELECT DISTINCT sz.value AS size
FROM Stock st
JOIN Sizes sz ON sz.id = st.size_id
WHERE st.quantity > 0
  AND st.size_id NOT IN (SELECT DISTINCT size_id FROM OrderItems)
ORDER BY sz.value;
