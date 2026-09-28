create extension if not exists vector;

drop table if exists price_history cascade;
drop table if exists products cascade;

create table if not exists products (
    id uuid default gen_random_uuid() primary key,
    user_id uuid,
    product_name text not null,
    model text,
    supplier text,
    price float8 not null,
    currency text default 'PKR',
    date date default current_date,
    source_file text default 'manual_entry',
    embedding vector(384),
    created_at timestamptz default timezone('utc'::text, now()) not null
);

create table if not exists price_history (
    id uuid default gen_random_uuid() primary key,
    product_id uuid references products(id) on delete cascade,
    price float8 not null,
    currency text default 'PKR',
    recorded_at timestamptz default timezone('utc'::text, now()) not null
);

create or replace function match_products (
    query_embedding vector(384),
    match_threshold float default 0.1,
    match_count int default 8
)
returns table (
    id uuid,
    product_name text,
    model text,
    supplier text,
    price float8,
    currency text,
    date date,
    source_file text,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        p.id,
        p.product_name,
        p.model,
        p.supplier,
        p.price,
        p.currency,
        p.date,
        p.source_file,
        1 - (p.embedding <=> query_embedding) as similarity
    from products p
    where p.embedding is not null
      and 1 - (p.embedding <=> query_embedding) > match_threshold
    order by p.embedding <=> query_embedding
    limit match_count;
end;
$$;