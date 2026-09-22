-- =============================================================================
-- REGOKEMON DATABASE SCHEMA (Supabase PostgreSQL)
-- Fokus: Katalog Kartu & Valuasi Harga (Tanpa Tabel Toko)
-- =============================================================================

-- 1. TABEL SETS (Ekspansi Seri Kartu)
CREATE TABLE IF NOT EXISTS public.sets (
    set_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    series TEXT,
    release_date DATE,
    release_year INT
);

-- 2. TABEL CARDS (Katalog Utama Kartu Pokemon)
CREATE TABLE IF NOT EXISTS public.cards (
    card_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    supertype TEXT,
    subtypes TEXT,
    types TEXT,
    hp FLOAT,
    number TEXT,
    rarity TEXT,
    artist TEXT,
    set_id TEXT REFERENCES public.sets(set_id) ON DELETE CASCADE,
    image_small TEXT,
    image_large TEXT
);

-- 3. TABEL CARD_PRICES (Valuasi & Harga Pasar)
CREATE TABLE IF NOT EXISTS public.card_prices (
    card_id TEXT PRIMARY KEY REFERENCES public.cards(card_id) ON DELETE CASCADE,
    tcg_normal_market NUMERIC(10,2),
    tcg_holo_market NUMERIC(10,2),
    tcg_reverse_market NUMERIC(10,2),
    cardmarket_trend NUMERIC(10,2),
    cardmarket_avg_sell NUMERIC(10,2),
    effective_market_price NUMERIC(10,2),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk mempercepat query pencarian, filter set, dan sorting harga
CREATE INDEX IF NOT EXISTS idx_cards_name ON public.cards(name);
CREATE INDEX IF NOT EXISTS idx_cards_set_id ON public.cards(set_id);
CREATE INDEX IF NOT EXISTS idx_cards_types ON public.cards(types);
CREATE INDEX IF NOT EXISTS idx_cards_rarity ON public.cards(rarity);
CREATE INDEX IF NOT EXISTS idx_card_prices_effective ON public.card_prices(effective_market_price);
