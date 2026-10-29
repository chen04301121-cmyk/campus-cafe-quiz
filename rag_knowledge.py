"""Knowledge documents for the RAG Text-to-SQL feature.

Each document is a small piece of text that will be stored in the vector
database. When a user asks a question, we retrieve the few documents that
are most similar to it and give them to the AI model as context.
"""

# Document kinds, kept as constants so other files can filter by them.
KIND_SCHEMA = "schema"
KIND_SEMANTICS = "semantics"
KIND_EXAMPLE = "example"


# 1. Database schema: tables, columns, and relationships.
SCHEMA_DOCS = [
    {
        "id": "schema_products",
        "kind": KIND_SCHEMA,
        "text": (
            "Table public.products stores the cafe menu. Columns: "
            "product_id (integer, primary key), "
            "product_name (text, for example 'Latte'), "
            "category (text: 'Coffee', 'Tea', or 'Food'), "
            "price (numeric, price of one unit in dollars)."
        ),
    },
    {
        "id": "schema_orders",
        "kind": KIND_SCHEMA,
        "text": (
            "Table public.orders stores customer orders. Columns: "
            "order_id (integer, primary key), "
            "product_id (integer, foreign key to products.product_id), "
            "quantity (integer, number of units ordered), "
            "order_date (date, between 2026-10-01 and 2026-10-03)."
        ),
    },
    {
        "id": "schema_relationship",
        "kind": KIND_SCHEMA,
        "text": (
            "Relationship: orders.product_id references products.product_id. "
            "To show a product name next to an order, JOIN orders with "
            "products ON orders.product_id = products.product_id."
        ),
    },
]


# 2. Business semantics: what the columns and common phrases mean.
SEMANTICS_DOCS = [
    {
        "id": "sem_units_sold",
        "kind": KIND_SEMANTICS,
        "text": (
            "Units sold, quantity sold, or sales volume means "
            "SUM(orders.quantity). Counting orders means COUNT(*) on the "
            "orders table, which is different from counting units."
        ),
    },
    {
        "id": "sem_revenue",
        "kind": KIND_SEMANTICS,
        "text": (
            "Revenue, income, or money earned means "
            "SUM(products.price * orders.quantity). It needs a JOIN "
            "between products and orders."
        ),
    },
    {
        "id": "sem_never_ordered",
        "kind": KIND_SEMANTICS,
        "text": (
            "Products that have never been ordered, or have no orders, "
            "are found with products LEFT JOIN orders and the filter "
            "WHERE orders.order_id IS NULL."
        ),
    },
    {
        "id": "sem_categories",
        "kind": KIND_SEMANTICS,
        "text": (
            "The category column only contains three values: 'Coffee', "
            "'Tea', and 'Food'. Drinks are Coffee or Tea. Text values "
            "are case sensitive, so write them exactly like this."
        ),
    },
    {
        "id": "sem_rules",
        "kind": KIND_SEMANTICS,
        "text": (
            "SQL rules for this database: it is PostgreSQL. Always write "
            "table names with the public. prefix. Write date literals as "
            "DATE 'YYYY-MM-DD'. Only generate a single SELECT query. "
            "Never modify data."
        ),
    },
]


# 3. Few-shot examples: a question paired with a correct SQL query.
# These are intentionally different from the five quiz questions so that
# the quiz answers are not leaked.
EXAMPLES = [
    (
        "How many orders were placed on October 2, 2026?",
        "SELECT COUNT(*) AS order_count\n"
        "FROM public.orders\n"
        "WHERE order_date = DATE '2026-10-02';",
    ),
    (
        "What is the average price of the products in each category?",
        "SELECT category, AVG(price) AS avg_price\n"
        "FROM public.products\n"
        "GROUP BY category\n"
        "ORDER BY category;",
    ),
    (
        "How much revenue did each product earn?",
        "SELECT p.product_name, SUM(p.price * o.quantity) AS revenue\n"
        "FROM public.products AS p\n"
        "JOIN public.orders AS o ON p.product_id = o.product_id\n"
        "GROUP BY p.product_id, p.product_name\n"
        "ORDER BY revenue DESC;",
    ),
    (
        "Which products cost more than 4 dollars?",
        "SELECT product_name, price\n"
        "FROM public.products\n"
        "WHERE price > 4\n"
        "ORDER BY price DESC;",
    ),
    (
        "On which date were the most units sold?",
        "SELECT order_date, SUM(quantity) AS total_units\n"
        "FROM public.orders\n"
        "GROUP BY order_date\n"
        "ORDER BY total_units DESC, order_date ASC\n"
        "LIMIT 1;",
    ),
    (
        "List the order IDs and product names of all tea orders.",
        "SELECT o.order_id, p.product_name\n"
        "FROM public.orders AS o\n"
        "JOIN public.products AS p ON o.product_id = p.product_id\n"
        "WHERE p.category = 'Tea'\n"
        "ORDER BY o.order_id;",
    ),
]


def build_documents():
    """Return every knowledge document as a list of dicts.

    Each dict has the keys: id, kind, text.
    """
    documents = list(SCHEMA_DOCS) + list(SEMANTICS_DOCS)
    for number, (question, sql) in enumerate(EXAMPLES, start=1):
        documents.append(
            {
                "id": f"example_{number}",
                "kind": KIND_EXAMPLE,
                "text": f"Question: {question}\nSQL:\n{sql}",
            }
        )
    return documents


if __name__ == "__main__":
    # Quick self-check: print how many documents of each kind exist.
    docs = build_documents()
    print(f"Total documents: {len(docs)}")
    for kind in (KIND_SCHEMA, KIND_SEMANTICS, KIND_EXAMPLE):
        count = sum(1 for doc in docs if doc["kind"] == kind)
        print(f"  {kind}: {count}")
