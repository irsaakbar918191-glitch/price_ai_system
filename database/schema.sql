CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.products (
    id BIGSERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    model TEXT,
    supplier TEXT,
    price DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'PKR',
    date DATE,
    source_file TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.product_embeddings (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION public.set_default_user_role()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_roles (user_id, role)
    VALUES (NEW.id, 'user')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trg_set_default_user_role
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.set_default_user_role();

ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read user_roles"
ON public.user_roles
FOR SELECT
USING (auth.uid() IS NOT NULL);

CREATE POLICY "Admins can write user_roles"
ON public.user_roles
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Admins can update user_roles"
ON public.user_roles
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Admins can delete user_roles"
ON public.user_roles
FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Authenticated users can read products"
ON public.products
FOR SELECT
USING (auth.uid() IS NOT NULL);

CREATE POLICY "Admins can insert products"
ON public.products
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Admins can update products"
ON public.products
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Admins can delete products"
ON public.products
FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Authenticated users can read embeddings"
ON public.product_embeddings
FOR SELECT
USING (auth.uid() IS NOT NULL);

CREATE POLICY "Admins can insert embeddings"
ON public.product_embeddings
FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Admins can update embeddings"
ON public.product_embeddings
FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE POLICY "Admins can delete embeddings"
ON public.product_embeddings
FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM public.user_roles ur
        WHERE ur.user_id = auth.uid()::text AND ur.role = 'admin'
    )
);

CREATE OR REPLACE FUNCTION public.match_products(query_embedding vector(384), match_count int DEFAULT 5)
RETURNS TABLE (
    id bigint,
    product_name text,
    model text,
    supplier text,
    price double precision,
    currency text,
    date date,
    source_file text,
    created_at timestamptz,
    similarity float
)
LANGUAGE sql
AS $$
    SELECT
        p.id,
        p.product_name,
        p.model,
        p.supplier,
        p.price,
        p.currency,
        p.date,
        p.source_file,
        p.created_at,
        1 - (pe.embedding <=> query_embedding) AS similarity
    FROM public.product_embeddings pe
    JOIN public.products p ON p.id = pe.product_id
    ORDER BY pe.embedding <=> query_embedding
    LIMIT match_count;
$$;

CREATE INDEX IF NOT EXISTS idx_products_name ON public.products(product_name);
CREATE INDEX IF NOT EXISTS idx_product_embeddings_product_id ON public.product_embeddings(product_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON public.products(supplier);
CREATE INDEX IF NOT EXISTS idx_product_embeddings_vector ON public.product_embeddings USING hnsw (embedding vector_cosine_ops);
