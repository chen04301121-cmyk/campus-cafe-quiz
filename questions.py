QUESTIONS = [
    {
        "id": 1,
        "title": "Find coffee products",
        "points": 4,
        "prompt": (
            "List the names and prices of all products in the Coffee "
            "category. Order by product_id ascending."
        ),
        "expected_sql": """
SELECT product_name, price
FROM public.products
WHERE category = 'Coffee'
ORDER BY product_id;
""",
        "expected_columns": ["product_name", "price"],
        "expected_rows": [
            ["Americano", 3.00],
            ["Latte", 4.50],
            ["Mocha", 5.00],
        ],
    },
    {
        "id": 2,
        "title": "Find the three most expensive products",
        "points": 4,
        "prompt": (
            "List the names and prices of the three most expensive "
            "products. Order by price descending, then product_id ascending."
        ),
        "expected_sql": """
SELECT product_name, price
FROM public.products
ORDER BY price DESC, product_id ASC
LIMIT 3;
""",
        "expected_columns": ["product_name", "price"],
        "expected_rows": [
            ["Mocha", 5.00],
            ["Latte", 4.50],
            ["Croissant", 4.00],
        ],
    },
    {
        "id": 3,
        "title": "View orders with product names",
        "points": 4,
        "prompt": (
            "For orders placed on October 1, 2026, show the order ID, "
            "product name, and quantity. Order by order_id ascending."
        ),
        "expected_sql": """
SELECT o.order_id, p.product_name, o.quantity
FROM public.orders AS o
JOIN public.products AS p
    ON o.product_id = p.product_id
WHERE o.order_date = DATE '2026-10-01'
ORDER BY o.order_id;
""",
        "expected_columns": ["order_id", "product_name", "quantity"],
        "expected_rows": [
            [1, "Americano", 2],
            [2, "Latte", 1],
            [3, "Croissant", 2],
        ],
    },
    {
        "id": 4,
        "title": "Calculate units sold per product",
        "points": 4,
        "prompt": (
            "For products with at least one order, show the product name "
            "and total quantity sold as total_quantity. Order by "
            "total_quantity descending, then product_id ascending."
        ),
        "expected_sql": """
SELECT p.product_name, SUM(o.quantity) AS total_quantity
FROM public.products AS p
JOIN public.orders AS o
    ON p.product_id = o.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_quantity DESC, p.product_id ASC;
""",
        "expected_columns": ["product_name", "total_quantity"],
        "expected_rows": [
            ["Latte", 6],
            ["Americano", 3],
            ["Mocha", 3],
            ["Croissant", 3],
            ["Green Tea", 2],
        ],
    },
    {
        "id": 5,
        "title": "Find products with no orders",
        "points": 4,
        "prompt": (
            "List the names of products that have never been ordered. "
            "Order by product_id ascending."
        ),
        "expected_sql": """
SELECT p.product_name
FROM public.products AS p
LEFT JOIN public.orders AS o
    ON p.product_id = o.product_id
WHERE o.order_id IS NULL
ORDER BY p.product_id;
""",
        "expected_columns": ["product_name"],
        "expected_rows": [
            ["Muffin"],
        ],
    },
]


if __name__ == "__main__":
    total_points = sum(question["points"] for question in QUESTIONS)
    print(f"Questions: {len(QUESTIONS)}")
    print(f"Total points: {total_points}")