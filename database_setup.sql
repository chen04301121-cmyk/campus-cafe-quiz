BEGIN;

CREATE TABLE public.products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC(6, 2) NOT NULL CHECK (price > 0)
);

CREATE TABLE public.orders (
    order_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL
        REFERENCES public.products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    order_date DATE NOT NULL
);

INSERT INTO public.products
    (product_id, product_name, category, price)
VALUES
    (1, 'Americano', 'Coffee', 3.00),
    (2, 'Latte', 'Coffee', 4.50),
    (3, 'Mocha', 'Coffee', 5.00),
    (4, 'Green Tea', 'Tea', 3.50),
    (5, 'Croissant', 'Food', 4.00),
    (6, 'Muffin', 'Food', 3.00);

INSERT INTO public.orders
    (order_id, product_id, quantity, order_date)
VALUES
    (1, 1, 2, '2026-10-01'),
    (2, 2, 1, '2026-10-01'),
    (3, 5, 2, '2026-10-01'),
    (4, 3, 1, '2026-10-02'),
    (5, 2, 3, '2026-10-02'),
    (6, 4, 2, '2026-10-02'),
    (7, 1, 1, '2026-10-03'),
    (8, 5, 1, '2026-10-03'),
    (9, 3, 2, '2026-10-03'),
    (10, 2, 2, '2026-10-03');

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;

CREATE ROLE quiz_reader NOLOGIN;
GRANT quiz_reader TO postgres;
GRANT USAGE ON SCHEMA public TO quiz_reader;
GRANT SELECT ON public.products, public.orders TO quiz_reader;

CREATE POLICY quiz_reader_products_select
ON public.products
FOR SELECT TO quiz_reader
USING (true);

CREATE POLICY quiz_reader_orders_select
ON public.orders
FOR SELECT TO quiz_reader
USING (true);

CREATE TABLE public.quiz_answers (
    user_id UUID NOT NULL
        REFERENCES auth.users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL
        CHECK (question_id BETWEEN 1 AND 5),
    answer_sql TEXT NOT NULL
        CHECK (char_length(answer_sql) BETWEEN 1 AND 10000),
    PRIMARY KEY (user_id, question_id)
);

ALTER TABLE public.quiz_answers ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.quiz_answers FROM PUBLIC, anon, quiz_reader;

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE
ON public.quiz_answers TO authenticated;

CREATE POLICY answers_select_own
ON public.quiz_answers
FOR SELECT TO authenticated
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY answers_insert_own
ON public.quiz_answers
FOR INSERT TO authenticated
WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY answers_update_own
ON public.quiz_answers
FOR UPDATE TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);

COMMIT;