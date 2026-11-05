// ==============================================================================
// frontend/src/services/supabaseService.js
// Layanan Pengambilan Data Langsung dari Supabase Cloud (20.617 Kartu Pokémon TCG)
// Berfungsi sebagai Direct Cloud Fallback agar Katalog & Set tetap berjalan 24/7
// di Vercel Production tanpa ketergantungan server backend lokal yang mati.
// ==============================================================================

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://rrvjtuylgiljaqvkavyk.supabase.co';
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_KEY || '';

const DEFAULT_USD_TO_IDR = 16000;

const headers = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
  Prefer: 'count=exact'
};

// 1. Ambil Daftar Sets Resmi Pokémon TCG
export async function fetchSetsFromSupabase(limit = 150) {
  try {
    const url = `${SUPABASE_URL}/rest/v1/sets?select=set_id,name,series,release_date,release_year&limit=${limit}&order=release_date.desc.nullslast`;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(`Supabase error: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('[SupabaseService] Gagal memuat sets:', err);
    return [];
  }
}

// 2. Ambil Data Kartu dengan Filter, Search, Sorting, dan Pagination
export async function fetchCardsFromSupabase({
  page = 1,
  limit = 20,
  search = '',
  supertype = 'all',
  rarity = 'all',
  holo = 'all',
  set_id = 'all',
  sortBy = 'newest'
} = {}) {
  const safeLimit = Math.max(1, Math.min(limit, 100));
  const safePage = Math.max(1, page);
  const offset = (safePage - 1) * safeLimit;

  const urlParts = [
    `${SUPABASE_URL}/rest/v1/cards`,
    `?select=card_id,name,supertype,rarity,image_small,sets(set_id,name,release_date),card_prices(effective_market_price)`,
    `&limit=${safeLimit}`,
    `&offset=${offset}`
  ];

  if (search && search.trim()) {
    urlParts.push(`&name=ilike.*${encodeURIComponent(search.trim())}*`);
  }

  if (supertype && supertype.toLowerCase() !== 'all') {
    urlParts.push(`&supertype=ilike.*${encodeURIComponent(supertype.trim())}*`);
  }

  if (rarity && rarity.toLowerCase() !== 'all') {
    urlParts.push(`&rarity=ilike.*${encodeURIComponent(rarity.trim())}*`);
  }

  if (holo && holo.toLowerCase() !== 'all') {
    if (holo.toLowerCase() === 'holo') {
      urlParts.push('&rarity=ilike.*Holo*');
    } else if (holo.toLowerCase() === 'non_holo') {
      urlParts.push('&rarity=not.ilike.*Holo*');
    }
  }

  if (set_id && set_id.toLowerCase() !== 'all') {
    urlParts.push(`&set_id=eq.${encodeURIComponent(set_id.trim())}`);
  }

  // Pengurutan
  if (sortBy === 'newest' || sortBy === 'release_desc') {
    urlParts.push('&order=sets(release_date).desc.nullslast,name.asc');
  } else if (sortBy === 'oldest' || sortBy === 'release_asc') {
    urlParts.push('&order=sets(release_date).asc.nullslast,name.asc');
  } else if (sortBy === 'price_desc') {
    urlParts.push('&order=card_prices(effective_market_price).desc.nullslast,name.asc');
  } else if (sortBy === 'price_asc') {
    urlParts.push('&order=card_prices(effective_market_price).asc.nullslast,name.asc');
  } else if (sortBy === 'name_asc') {
    urlParts.push('&order=name.asc');
  } else if (sortBy === 'name_desc') {
    urlParts.push('&order=name.desc');
  }

  const fullUrl = urlParts.join('');

  try {
    const res = await fetch(fullUrl, { headers });
    if (!res.ok) throw new Error(`Supabase status: ${res.status}`);

    const data = await res.json();
    const contentRange = res.headers.get('content-range') || '';
    let totalCount = data.length;
    if (contentRange.includes('/')) {
      const parts = contentRange.split('/');
      const parsed = parseInt(parts[1], 10);
      if (!isNaN(parsed)) totalCount = parsed;
    }

    const formattedCards = data.map(item => {
      let priceVal = 0.0;
      if (item.card_prices && typeof item.card_prices === 'object') {
        if (Array.isArray(item.card_prices) && item.card_prices.length > 0) {
          priceVal = item.card_prices[0].effective_market_price || 0.0;
        } else if (item.card_prices.effective_market_price) {
          priceVal = item.card_prices.effective_market_price;
        }
      }

      let setInfo = 'unknown';
      if (item.sets && typeof item.sets === 'object') {
        if (Array.isArray(item.sets) && item.sets.length > 0) {
          setInfo = item.sets[0].set_id || 'unknown';
        } else if (item.sets.set_id) {
          setInfo = item.sets.set_id;
        }
      }

      const rarityStr = item.rarity || 'Common';
      const words = rarityStr.split(' ');
      let rarityIcon = words.map(w => w[0]?.toUpperCase() || '').join('');
      if (rarityIcon.length > 2) rarityIcon = rarityIcon.slice(0, 2);

      const isUnlisted = !priceVal || priceVal <= 0;
      const priceUsdStr = isUnlisted ? 'Unlisted' : `$ ${priceVal.toFixed(2)}`;
      const priceIdrVal = Math.round(priceVal * DEFAULT_USD_TO_IDR);
      const priceIdrStr = isUnlisted
        ? 'Belum Ada Data'
        : `Rp ${priceIdrVal.toLocaleString('id-ID')}`;

      return {
        id: item.card_id,
        name: item.name,
        supertype: item.supertype || 'Pokémon',
        price: priceUsdStr,
        price_usd: priceUsdStr,
        price_idr: priceIdrStr,
        price_num: priceVal,
        is_unlisted: isUnlisted,
        rarityText: rarityStr,
        rarityIcon: rarityIcon || 'C',
        set: setInfo,
        image: item.image_small || '/card-result.png'
      };
    });

    return {
      total: totalCount,
      page: safePage,
      limit: safeLimit,
      total_pages: Math.ceil(totalCount / safeLimit) || 1,
      currency_rate: DEFAULT_USD_TO_IDR,
      cards: formattedCards
    };
  } catch (err) {
    console.error('[SupabaseService] Gagal mengambil kartu dari Supabase:', err);
    throw err;
  }
}

// 3. Ambil Riwayat Harga Kartu Tertentu
export async function fetchCardHistoryFromSupabase(cardId) {
  try {
    const url = `${SUPABASE_URL}/rest/v1/card_price_history?select=recorded_date,effective_market_price&card_id=eq.${cardId}&order=recorded_date.asc`;
    const res = await fetch(url, { headers });
    if (!res.ok) return [];
    return await res.json();
  } catch (err) {
    console.error('[SupabaseService] Gagal memuat riwayat harga:', err);
    return [];
  }
}

