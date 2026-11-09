import React, { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import './Marketplace.css';

const USD_TO_IDR = 16285;

function formatIdr(usd) {
  const idr = Math.round((usd || 0) * USD_TO_IDR);
  return 'Rp ' + idr.toLocaleString('id-ID');
}

function maskPhoneNumber(phone) {
  const clean = (phone || '').replace(/\s+/g, '');
  if (clean.length < 8) return clean || '-';
  return clean.slice(0, 4) + '-xxxx-' + clean.slice(-4);
}

// Kompres gambar yang diunggah ke DataURL JPEG ringkas agar aman disimpan di localStorage
function compressImageFile(file, maxWidth = 600, quality = 0.82) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const scale = img.width > maxWidth ? maxWidth / img.width : 1;
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = reject;
      img.src = event.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// ==========================================
// 1. DATA LISTING KARTU ORGANIK AWAL
// ==========================================
const INITIAL_ORGANIC_CARDS = [
  {
    id: 'sv8-116',
    name: 'Koraidon',
    cardNumber: '116/191',
    set: 'SSP',
    setName: 'Surging Sparks',
    releaseDate: '2024-11-08',
    rarityText: 'Uncommon',
    condition: 'Mint',
    conditionCode: 'M',
    language: 'EN',
    price_num: 1.25,
    marketRefUsd: 1.10,
    stock: 1,
    sellerId: 'seller-pokevault',
    sellerName: 'PokeVault Jakarta',
    sellerOwner: 'Dimas Prakoso',
    sellerPhone: '081288901122',
    sellerCity: 'Jakarta Selatan',
    sellerJoined: 'Mei 2024',
    sellerNote: 'Kartu fisik original dari booster pack Surging Sparks. Sudut dan permukaan bersih tanpa lekukan, difoto langsung di atas stand akrilik.',
    image: '/organic-cards/Koraidon sv8-116.jpeg',
  },
  {
    id: 'sv8-172',
    name: 'Dragon Elixir',
    cardNumber: '172/191',
    set: 'SSP',
    setName: 'Surging Sparks',
    releaseDate: '2024-11-08',
    rarityText: 'Uncommon',
    condition: 'Near Mint',
    conditionCode: 'NM',
    language: 'EN',
    price_num: 0.90,
    marketRefUsd: 0.85,
    stock: 2,
    sellerId: 'seller-cardmaster',
    sellerName: 'CardMaster Surabaya',
    sellerOwner: 'Rizky Hidayat',
    sellerPhone: '081334556677',
    sellerCity: 'Surabaya',
    sellerJoined: 'Januari 2024',
    sellerNote: 'Kartu Trainer Item kompetitif. Kondisi Near Mint, potongan tepi rapi dan langsung dimasukkan ke dalam inner sleeve.',
    image: '/organic-cards/Dragon Elixir sv8-172.jpeg',
  },
  {
    id: 'me2pt5-64',
    name: 'Heliolisk',
    cardNumber: '064/217',
    set: 'ASC',
    setName: 'Ascended Heroes',
    releaseDate: '2026-01-30',
    rarityText: 'Reverse Holo',
    condition: 'Lightly Played',
    conditionCode: 'LP',
    language: 'EN',
    price_num: 2.40,
    marketRefUsd: 2.50,
    stock: 1,
    sellerId: 'seller-bandunghobby',
    sellerName: 'Bandung Hobby Hub',
    sellerOwner: 'Fajar Nugraha',
    sellerPhone: '082119887766',
    sellerCity: 'Bandung',
    sellerJoined: 'Agustus 2024',
    sellerNote: 'Varian Reverse Holofoil dengan efek kilau foil utuh. Terdapat sedikit gesekan halus pada tepi kanan bawah sesuai foto organik.',
    image: '/organic-cards/Heliolisk me2pt5-64.webp',
  },
  {
    id: 'me5-6',
    name: 'Sinistcha',
    cardNumber: '006/084',
    set: 'PBL',
    setName: 'Pitch Black',
    releaseDate: '2026-07-17',
    rarityText: 'Uncommon',
    condition: 'Near Mint',
    conditionCode: 'NM',
    language: 'EN',
    price_num: 1.10,
    marketRefUsd: 1.15,
    stock: 1,
    sellerId: 'seller-kanto',
    sellerName: 'KantoCollectors ID',
    sellerOwner: 'Kevin Wijaya',
    sellerPhone: '085711223344',
    sellerCity: 'Jakarta Barat',
    sellerJoined: 'Maret 2024',
    sellerNote: 'Ilustrasi mingo seri Pitch Black. Kondisi kartu sangat terawat, permukaan depan dan belakang bersih dari goresan.',
    image: '/organic-cards/Sinistcha me5-6.jpeg',
  },
  {
    id: 'sv8-188',
    name: 'Technical Machine: Fluorite',
    cardNumber: '188/191',
    set: 'SSP',
    setName: 'Surging Sparks',
    releaseDate: '2024-11-08',
    rarityText: 'Uncommon',
    condition: 'Near Mint',
    conditionCode: 'NM',
    language: 'EN',
    price_num: 0.85,
    marketRefUsd: 0.80,
    stock: 3,
    sellerId: 'seller-nusantara',
    sellerName: 'Nusantara TCG',
    sellerOwner: 'Bagas Adi',
    sellerPhone: '087855664433',
    sellerCity: 'Yogyakarta',
    sellerJoined: 'Juni 2024',
    sellerNote: 'Kartu Pokemon Tool untuk deck Tera. Kondisi fisik mulus, centering seimbang, siap pakai untuk turnamen maupun koleksi.',
    image: '/organic-cards/Fluorite sv8-188.jpeg',
  },
  {
    id: 'me5-32',
    name: 'Jynx',
    cardNumber: '032/084',
    set: 'PBL',
    setName: 'Pitch Black',
    releaseDate: '2026-07-17',
    rarityText: 'Common',
    condition: 'Near Mint',
    conditionCode: 'NM',
    language: 'EN',
    price_num: 0.75,
    marketRefUsd: 0.75,
    stock: 2,
    sellerId: 'seller-tokyotcg',
    sellerName: 'TokyoTCG Direct',
    sellerOwner: 'Hendra Saputra',
    sellerPhone: '081900112233',
    sellerCity: 'Bandung',
    sellerJoined: 'Februari 2024',
    sellerNote: 'Ilustrasi Yoshimoto Yoshimon. Difoto langsung di atas playmat, keempat sudut kartu masih tajam tanpa whitening.',
    image: '/organic-cards/Jynx me5-32.jpeg',
  },
  {
    id: 'sv8pt5-77',
    name: 'Hoothoot',
    cardNumber: '077/131',
    set: 'PRE',
    setName: 'Prismatic Evolutions',
    releaseDate: '2025-01-17',
    rarityText: 'Common',
    condition: 'Near Mint',
    conditionCode: 'NM',
    language: 'EN',
    price_num: 0.65,
    marketRefUsd: 0.70,
    stock: 1,
    sellerId: 'seller-grailed',
    sellerName: 'GrailedPoke ID',
    sellerOwner: 'Arif Rahman',
    sellerPhone: '081199882211',
    sellerCity: 'Jakarta Pusat',
    sellerJoined: 'April 2024',
    sellerNote: 'Seri Prismatic Evolutions ilustrasi Nakamura Ippan. Kondisi kartu bersih dan disimpan di dalam binder bebas asam.',
    image: '/organic-cards/Hoothoot sv8pt5-77.jpeg',
  },
  {
    id: 'me2pt5-80',
    name: 'Togepi',
    cardNumber: '070/191',
    set: 'ASC',
    setName: 'Ascended Heroes',
    releaseDate: '2026-01-30',
    rarityText: 'Common',
    condition: 'Lightly Played',
    conditionCode: 'LP',
    language: 'EN',
    price_num: 0.95,
    marketRefUsd: 0.90,
    stock: 1,
    sellerId: 'seller-pokevault',
    sellerName: 'PokeVault Jakarta',
    sellerOwner: 'Dimas Prakoso',
    sellerPhone: '081288901122',
    sellerCity: 'Jakarta Selatan',
    sellerJoined: 'Mei 2024',
    sellerNote: 'Foto fisik langsung (on-cam). Terdapat sedikit tanda pemakaian ringan di sudut atas, selebihnya ilustrasi tetap bersih.',
    image: '/organic-cards/Togepi me2pt5-80 oncam.webp',
  },
];

const DEMO_SELLER_ACCOUNT = {
  id: 'seller-demo-user',
  fullName: 'Raka Pratama',
  storeName: 'Garuda PokeStore',
  phone: '081234567890',
  email: 'raka@garudapoke.id',
  city: 'Surabaya',
  address: 'Jl. Raya Gubeng No. 45, Kec. Gubeng, Surabaya',
  joinedAt: 'November 2026',
};

const CONDITION_OPTIONS = [
  { code: 'M', label: 'Mint', desc: 'Kondisi sempurna setara baru keluar dari pack, 4 sudut tajam tanpa goresan.' },
  { code: 'NM', label: 'Near Mint', desc: 'Sangat mulus, maksimal 1 titik whitening mikro yang hampir tidak terlihat.' },
  { code: 'LP', label: 'Lightly Played', desc: 'Terdapat whitening ringan di tepi/sudut atau goresan halus minor pada permukaan.' },
  { code: 'MP', label: 'Moderately Played', desc: 'Tanda pemakaian terlihat jelas pada tepi kartu, namun kartu tetap layak main.' },
];

// ==========================================
// 2. KOMPONEN IKON SVG (BEBAS EMOTIKON)
// ==========================================
const SearchIcon = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#475086" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  </svg>
);

const BookmarkIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} width="100%" height="100%" fill="currentColor">
    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
  </svg>
);

const CartIcon = ({ className }) => (
  <svg viewBox="0 0 24 24" className={className} width="19" height="19" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="9" cy="21" r="1"></circle>
    <circle cx="20" cy="21" r="1"></circle>
    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
  </svg>
);

const UserIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
    <circle cx="12" cy="7" r="4"></circle>
  </svg>
);

const PlusIcon = () => (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  </svg>
);

const UploadPhotoIcon = () => (
  <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#555c8f" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
    <circle cx="8.5" cy="8.5" r="1.5"></circle>
    <polyline points="21 15 16 10 5 21"></polyline>
  </svg>
);

const ChevronDownIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#475086" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
  </svg>
);

const FlagBadge = ({ lang }) => {
  return <span className="mk-flag-label" title={`Wilayah Rilis: ${lang}`}>{lang}</span>;
};

const RarityIcon = ({ type }) => {
  if (type === 'circle') return <span className="mk-symbol-circle"></span>;
  if (type === 'diamond') return <span className="mk-symbol-diamond"></span>;
  if (type === 'star') return (
    <svg viewBox="0 0 24 24" width="10" height="10" fill="#f59e0b" className="mk-symbol-star">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
    </svg>
  );
  if (type === 'double-star') return (
    <div className="mk-symbol-double">
      <svg viewBox="0 0 24 24" width="10" height="10" fill="#1e293b">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
      </svg>
      <svg viewBox="0 0 24 24" width="10" height="10" fill="#1e293b" style={{ marginLeft: '-4px' }}>
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
      </svg>
    </div>
  );
  return null;
};

function getRarityMeta(rarityStr) {
  const r = (rarityStr || '').toLowerCase();
  if (r.includes('special') || r.includes('hyper') || r.includes('secret')) {
    return { symbol: 'double-star', abbr: 'SAR' };
  }
  if (r.includes('ultra') || r.includes('illustration') || r.includes('double')) {
    return { symbol: 'star', abbr: 'AR' };
  }
  if (r.includes('reverse') || r.includes('holo')) {
    return { symbol: 'star', abbr: 'RH' };
  }
  if (r.includes('rare')) {
    return { symbol: 'star', abbr: 'R' };
  }
  if (r.includes('uncommon')) {
    return { symbol: 'diamond', abbr: 'U' };
  }
  return { symbol: 'circle', abbr: 'C' };
}

// ==========================================
// 3. KOMPONEN UTAMA MARKETPLACE
// ==========================================
export default function Marketplace() {
  // 1. State Akun Pengguna / Pelapak (Tersimpan di localStorage)
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('regokemon_active_user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  // Daftar akun terdaftar di browser
  const [registeredUsers, setRegisteredUsers] = useState(() => {
    try {
      const savedList = localStorage.getItem('regokemon_registered_users');
      return savedList ? JSON.parse(savedList) : [DEMO_SELLER_ACCOUNT];
    } catch {
      return [DEMO_SELLER_ACCOUNT];
    }
  });

  // 2. State Listing Tambahan User (Tersimpan di localStorage agar tidak hilang saat refresh)
  const [customListings, setCustomListings] = useState(() => {
    try {
      const savedCustom = localStorage.getItem('regokemon_custom_listings_v1');
      return savedCustom ? JSON.parse(savedCustom) : [];
    } catch {
      return [];
    }
  });

  // Daftar ID kartu awal yang dihapus oleh user (jika ada)
  const [removedInitialIds, setRemovedInitialIds] = useState(() => {
    try {
      const savedRemoved = localStorage.getItem('regokemon_removed_initial_ids');
      return savedRemoved ? JSON.parse(savedRemoved) : [];
    } catch {
      return [];
    }
  });

  // Gabungan listing kustom + 8 kartu organik awal
  const marketCards = useMemo(() => {
    const activeInitial = INITIAL_ORGANIC_CARDS.filter((c) => !removedInitialIds.includes(c.id));
    return [...customListings, ...activeInitial];
  }, [customListings, removedInitialIds]);

  // 3. State Riwayat Pesanan (Orders)
  const [orderHistory, setOrderHistory] = useState(() => {
    try {
      const savedOrders = localStorage.getItem('regokemon_order_history');
      return savedOrders ? JSON.parse(savedOrders) : [];
    } catch {
      return [];
    }
  });

  // 4. State Filter & Pencarian
  const [searchInput, setSearchInput] = useState('');
  const [sortBy, setSortBy] = useState('name_asc');
  const [selectedRarity, setSelectedRarity] = useState('all');
  const [selectedLanguage, setSelectedLanguage] = useState('all');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [onlyWishlistGrid, setOnlyWishlistGrid] = useState(false);

  // 5. State Modal & Navigasi Panel
  const [selectedCard, setSelectedCard] = useState(null);
  const [isClosingModal, setIsClosingModal] = useState(false);
  const selectedCardRef = useRef(selectedCard);
  useEffect(() => {
    selectedCardRef.current = selectedCard;
  }, [selectedCard]);

  const handleCloseModal = () => {
    setIsClosingModal(true);
    setTimeout(() => {
      setSelectedCard(null);
      setIsClosingModal(false);
    }, 200);
  };
  const [revealSellerPhone, setRevealSellerPhone] = useState(false);
  const [isSellModalOpen, setIsSellModalOpen] = useState(false);

  // Auth Modal ('login' | 'register') & aksi tertunda ('sell' | 'checkout' | null)
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authTab, setAuthTab] = useState('login');
  const [pendingAction, setPendingAction] = useState(null);
  const [authError, setAuthError] = useState('');

  // Account Modal ('profile' | 'listings' | 'orders')
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);
  const [accountTab, setAccountTab] = useState('profile');
  const [profileSavedNotice, setProfileSavedNotice] = useState('');

  // Form Login & Register
  const [loginForm, setLoginForm] = useState({ identifier: '', password: '' });
  const [registerForm, setRegisterForm] = useState({
    fullName: '',
    storeName: '',
    phone: '',
    email: '',
    city: '',
    address: '',
    password: '',
  });
  const [profileEditForm, setProfileEditForm] = useState({
    fullName: '',
    storeName: '',
    phone: '',
    email: '',
    city: '',
    address: '',
  });

  // State Drawer: 'saved' | 'cart' | null
  const [activeDrawer, setActiveDrawer] = useState(null);
  const [checkoutReceipt, setCheckoutReceipt] = useState(null);
  const [selectedCourier, setSelectedCourier] = useState('reguler');
  const [selectedPayment, setSelectedPayment] = useState('QRIS');

  // 6. State Saved Items / Wishlist
  const [savedCards, setSavedCards] = useState(() => {
    try {
      const saved = localStorage.getItem('regokemon_saved_cards_v2');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) return parsed;
      }
      return INITIAL_ORGANIC_CARDS.slice(0, 3);
    } catch {
      return INITIAL_ORGANIC_CARDS.slice(0, 3);
    }
  });

  // 7. State Cart / Keranjang Belanja
  const [cartItems, setCartItems] = useState(() => {
    try {
      const savedCart = localStorage.getItem('regokemon_cart_items');
      if (savedCart) {
        const parsed = JSON.parse(savedCart);
        if (Array.isArray(parsed)) return parsed;
      }
      return [INITIAL_ORGANIC_CARDS[0]];
    } catch {
      return [INITIAL_ORGANIC_CARDS[0]];
    }
  });

  // 8. State Form "Jual Kartu"
  const fileInputRef = useRef(null);
  const [sellForm, setSellForm] = useState({
    photoPreview: '',
    name: '',
    cardNumber: '',
    set: '',
    setName: '',
    rarityText: 'Uncommon',
    language: 'EN',
    conditionCode: 'NM',
    priceUsd: '',
    sellerNote: '',
  });
  const [sellError, setSellError] = useState('');

  // Sinkronisasi state ke localStorage
  useEffect(() => {
    try {
      if (currentUser) {
        localStorage.setItem('regokemon_active_user', JSON.stringify(currentUser));
      } else {
        localStorage.removeItem('regokemon_active_user');
      }
    } catch (err) {
      console.error('Gagal menyimpan sesi user:', err);
    }
  }, [currentUser]);

  useEffect(() => {
    try {
      localStorage.setItem('regokemon_registered_users', JSON.stringify(registeredUsers));
    } catch (err) {
      console.error('Gagal menyimpan daftar user:', err);
    }
  }, [registeredUsers]);

  useEffect(() => {
    try {
      localStorage.setItem('regokemon_custom_listings_v1', JSON.stringify(customListings));
    } catch (err) {
      console.error('Gagal menyimpan listing kustom:', err);
    }
  }, [customListings]);

  useEffect(() => {
    try {
      localStorage.setItem('regokemon_removed_initial_ids', JSON.stringify(removedInitialIds));
    } catch (err) {
      console.error('Gagal menyimpan ID terhapus:', err);
    }
  }, [removedInitialIds]);

  useEffect(() => {
    try {
      localStorage.setItem('regokemon_order_history', JSON.stringify(orderHistory));
    } catch (err) {
      console.error('Gagal menyimpan riwayat pesanan:', err);
    }
  }, [orderHistory]);

  useEffect(() => {
    try {
      localStorage.setItem('regokemon_saved_cards_v2', JSON.stringify(savedCards));
    } catch (err) {
      console.error('Gagal menyimpan wishlist:', err);
    }
  }, [savedCards]);

  useEffect(() => {
    try {
      localStorage.setItem('regokemon_cart_items', JSON.stringify(cartItems));
    } catch (err) {
      console.error('Gagal menyimpan keranjang:', err);
    }
  }, [cartItems]);

  // Tutup Drawer atau Modal dengan tombol Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setActiveDrawer(null);
        if (selectedCardRef.current) {
          handleCloseModal();
        }
        setIsSellModalOpen(false);
        setIsAuthModalOpen(false);
        setIsAccountModalOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fungsi Buka Modal Jual Kartu (Wajib Login terlebih dahulu)
  const handleOpenSellModal = () => {
    setSellError('');
    if (!currentUser) {
      setPendingAction('sell');
      setAuthError('');
      setAuthTab('login');
      setIsAuthModalOpen(true);
      return;
    }
    setIsSellModalOpen(true);
  };

  // Fungsi Buka Modal Akun Saya
  const handleOpenAccountModal = (defaultTab = 'profile') => {
    if (!currentUser) {
      setPendingAction(null);
      setAuthError('');
      setAuthTab('login');
      setIsAuthModalOpen(true);
      return;
    }
    setProfileEditForm({
      fullName: currentUser.fullName || '',
      storeName: currentUser.storeName || '',
      phone: currentUser.phone || '',
      email: currentUser.email || '',
      city: currentUser.city || '',
      address: currentUser.address || '',
    });
    setProfileSavedNotice('');
    setAccountTab(defaultTab);
    setIsAccountModalOpen(true);
  };

  // Selesaikan proses setelah user berhasil Login / Register
  const completeAuthSuccess = (userObj) => {
    setCurrentUser(userObj);
    setIsAuthModalOpen(false);
    setAuthError('');
    if (pendingAction === 'sell') {
      setPendingAction(null);
      setIsSellModalOpen(true);
    } else if (pendingAction === 'checkout') {
      setPendingAction(null);
      setActiveDrawer('cart');
    }
  };

  // Handler Submit Login
  const handleLoginSubmit = (e) => {
    e.preventDefault();
    const idClean = loginForm.identifier.trim().toLowerCase();
    if (!idClean || !loginForm.password.trim()) {
      setAuthError('Masukkan email atau nomor HP beserta kata sandi.');
      return;
    }

    const found = registeredUsers.find(
      (u) =>
        (u.email && u.email.toLowerCase() === idClean) ||
        (u.phone && u.phone.replace(/\s+/g, '') === idClean) ||
        (u.storeName && u.storeName.toLowerCase() === idClean)
    );

    if (found) {
      completeAuthSuccess(found);
    } else {
      setAuthError('Akun belum terdaftar. Silakan buat akun pada tab Daftar terlebih dahulu.');
    }
  };

  // Handler Submit Register
  const handleRegisterSubmit = (e) => {
    e.preventDefault();
    if (
      !registerForm.fullName.trim() ||
      !registerForm.storeName.trim() ||
      !registerForm.phone.trim() ||
      !registerForm.city.trim() ||
      !registerForm.password.trim()
    ) {
      setAuthError('Nama lengkap, nama toko, nomor WhatsApp/HP, kota, dan kata sandi wajib diisi.');
      return;
    }

    const newUser = {
      id: 'seller-' + Date.now(),
      fullName: registerForm.fullName.trim(),
      storeName: registerForm.storeName.trim(),
      phone: registerForm.phone.trim(),
      email: registerForm.email.trim() || `${registerForm.storeName.trim().toLowerCase().replace(/\s+/g, '')}@regokemon.id`,
      city: registerForm.city.trim(),
      address: registerForm.address.trim() || `Kota ${registerForm.city.trim()}`,
      joinedAt: 'November 2026',
    };

    setRegisteredUsers((prev) => [newUser, ...prev]);
    completeAuthSuccess(newUser);
  };

  // Handler Simpan Perubahan Profil & Identitas Penjual
  const handleSaveProfile = (e) => {
    e.preventDefault();
    if (!profileEditForm.fullName.trim() || !profileEditForm.storeName.trim() || !profileEditForm.phone.trim()) {
      return;
    }
    const updatedUser = {
      ...currentUser,
      fullName: profileEditForm.fullName.trim(),
      storeName: profileEditForm.storeName.trim(),
      phone: profileEditForm.phone.trim(),
      email: profileEditForm.email.trim(),
      city: profileEditForm.city.trim(),
      address: profileEditForm.address.trim(),
    };
    setCurrentUser(updatedUser);
    setRegisteredUsers((prev) =>
      prev.map((u) => (u.id === updatedUser.id ? updatedUser : u))
    );
    // Perbarui juga identitas penjual pada listing milik user ini
    setCustomListings((prev) =>
      prev.map((item) =>
        item.sellerId === updatedUser.id
          ? {
              ...item,
              sellerName: updatedUser.storeName,
              sellerOwner: updatedUser.fullName,
              sellerPhone: updatedUser.phone,
              sellerCity: updatedUser.city,
            }
          : item
      )
    );
    setProfileSavedNotice('Identitas penjual berhasil diperbarui.');
  };

  // Fungsi Hapus Listing milik sendiri
  const handleDeleteListing = (cardId) => {
    setCustomListings((prev) => prev.filter((item) => item.id !== cardId));
    setRemovedInitialIds((prev) => (prev.includes(cardId) ? prev : [...prev, cardId]));
    setSavedCards((prev) => prev.filter((item) => item.id !== cardId));
    setCartItems((prev) => prev.filter((item) => item.id !== cardId));
    if (selectedCard && selectedCard.id === cardId) {
      setSelectedCard(null);
    }
  };

  // Fungsi Wishlist / Saved Items
  const isCardSaved = (cardId) => savedCards.some((item) => item.id === cardId);

  const toggleSaveCard = (card) => {
    setSavedCards((prev) => {
      const exists = prev.some((item) => item.id === card.id);
      return exists ? prev.filter((item) => item.id !== card.id) : [...prev, card];
    });
  };

  const removeSavedCard = (cardId) => {
    setSavedCards((prev) => prev.filter((item) => item.id !== cardId));
  };

  const clearSavedCards = () => {
    setSavedCards([]);
    setOnlyWishlistGrid(false);
  };

  // Fungsi Cart / Keranjang Belanja
  const isCardInCart = (cardId) => cartItems.some((item) => item.id === cardId);

  const toggleCartItem = (card) => {
    setCheckoutReceipt(null);
    setCartItems((prev) => {
      const exists = prev.some((item) => item.id === card.id);
      return exists ? prev.filter((item) => item.id !== card.id) : [...prev, card];
    });
  };

  const moveSavedToCart = (card) => {
    setCheckoutReceipt(null);
    if (!isCardInCart(card.id)) {
      setCartItems((prev) => [...prev, card]);
    }
    setActiveDrawer('cart');
  };

  const removeCartItem = (cardId) => {
    setCartItems((prev) => prev.filter((item) => item.id !== cardId));
  };

  const courierFeeUsd = selectedCourier === 'ekspres' ? 0.85 : 0.45;
  const protectionFeeUsd = cartItems.length > 0 ? 0.35 : 0;
  const subtotalCartUsd = useMemo(
    () => cartItems.reduce((sum, item) => sum + (item.price_num || 0), 0),
    [cartItems]
  );
  const totalCartUsd = cartItems.length > 0 ? subtotalCartUsd + protectionFeeUsd + courierFeeUsd : 0;

  const handleCheckoutCart = () => {
    if (cartItems.length === 0) return;
    if (!currentUser) {
      setActiveDrawer(null);
      setPendingAction('checkout');
      setAuthError('Silakan masuk ke akun Anda terlebih dahulu untuk melanjutkan pengiriman dan pembayaran.');
      setAuthTab('login');
      setIsAuthModalOpen(true);
      return;
    }

    const newOrder = {
      orderId: 'RGK-' + String(Date.now()).slice(-6),
      createdAt: new Date().toLocaleDateString('id-ID', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }),
      buyerName: currentUser.fullName,
      buyerPhone: currentUser.phone,
      shippingAddress: currentUser.address || currentUser.city,
      courier: selectedCourier === 'ekspres' ? 'Regokemon Safe Express (1-2 Hari)' : 'Reguler Toploader Box (2-4 Hari)',
      paymentMethod: selectedPayment,
      itemCount: cartItems.length,
      items: [...cartItems],
      totalUsd: totalCartUsd,
      totalIdr: formatIdr(totalCartUsd),
    };

    setCheckoutReceipt(newOrder);
    setOrderHistory((prev) => [newOrder, ...prev]);
    setCartItems([]);
  };

  // Handler Upload File Foto Fisik pada Modal "Jual Kartu" (Kompresi ke Base64 agar tahan refresh)
  const handleFileChange = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try {
      const compressedDataUrl = await compressImageFile(file);
      const baseName = file.name.replace(/\.[^/.]+$/, '');
      setSellForm((prev) => ({
        ...prev,
        photoPreview: compressedDataUrl,
        name: prev.name || baseName,
      }));
      setSellError('');
    } catch {
      setSellError('Gagal memproses file gambar. Pastikan format file adalah JPG, PNG, atau WEBP.');
    }
  };

  // Handler Submit Listing Baru ("Jual Kartu") menggunakan Identitas Akun Aktif
  const handleSubmitSellForm = (e) => {
    e.preventDefault();
    if (!currentUser) {
      setIsSellModalOpen(false);
      setPendingAction('sell');
      setIsAuthModalOpen(true);
      return;
    }
    if (!sellForm.photoPreview) {
      setSellError('Unggah foto fisik kartu dari perangkat Anda terlebih dahulu.');
      return;
    }
    if (!sellForm.name.trim() || !sellForm.priceUsd) {
      setSellError('Nama kartu dan harga jual wajib diisi.');
      return;
    }

    const parsedPrice = Math.max(0.1, parseFloat(sellForm.priceUsd) || 1.0);
    const condObj = CONDITION_OPTIONS.find((c) => c.code === sellForm.conditionCode) || CONDITION_OPTIONS[1];
    const todayStr = new Date().toISOString().slice(0, 10);

    const newListing = {
      id: 'listing-' + Date.now(),
      name: sellForm.name.trim(),
      cardNumber: sellForm.cardNumber.trim() || '001/191',
      set: (sellForm.set.trim() || 'SSP').toUpperCase(),
      setName: sellForm.setName.trim() || 'Koleksi Komunitas',
      releaseDate: todayStr,
      rarityText: sellForm.rarityText,
      condition: condObj.label,
      conditionCode: condObj.code,
      language: sellForm.language,
      price_num: parsedPrice,
      marketRefUsd: Number((parsedPrice * 0.95).toFixed(2)),
      stock: 1,
      sellerId: currentUser.id,
      sellerName: currentUser.storeName,
      sellerOwner: currentUser.fullName,
      sellerPhone: currentUser.phone,
      sellerCity: currentUser.city,
      sellerJoined: currentUser.joinedAt || 'November 2026',
      sellerNote:
        sellForm.sellerNote.trim() ||
        `${condObj.label} (${condObj.code}). ${condObj.desc}`,
      image: sellForm.photoPreview,
    };

    setCustomListings((prev) => [newListing, ...prev]);
    setIsSellModalOpen(false);
    setSellError('');
    setSellForm({
      photoPreview: '',
      name: '',
      cardNumber: '',
      set: '',
      setName: '',
      rarityText: 'Uncommon',
      language: 'EN',
      conditionCode: 'NM',
      priceUsd: '',
      sellerNote: '',
    });
  };

  // Filter & Sortir Katalog Kartu Organik
  const filteredCards = useMemo(() => {
    const query = searchInput.trim().toLowerCase();
    const minVal = minPrice !== '' ? parseFloat(minPrice) : null;
    const maxVal = maxPrice !== '' ? parseFloat(maxPrice) : null;

    const list = marketCards.filter((card) => {
      if (onlyWishlistGrid && !savedCards.some((s) => s.id === card.id)) {
        return false;
      }

      if (query) {
        const matchName = card.name.toLowerCase().includes(query);
        const matchSet = card.set.toLowerCase().includes(query) || card.setName.toLowerCase().includes(query);
        const matchId = card.id.toLowerCase().includes(query) || card.cardNumber.toLowerCase().includes(query);
        const matchSeller =
          card.sellerName.toLowerCase().includes(query) ||
          (card.sellerOwner && card.sellerOwner.toLowerCase().includes(query)) ||
          (card.sellerCity && card.sellerCity.toLowerCase().includes(query));
        if (!matchName && !matchSet && !matchId && !matchSeller) return false;
      }

      if (selectedRarity !== 'all' && card.rarityText !== selectedRarity) {
        return false;
      }

      if (selectedLanguage !== 'all' && card.language !== selectedLanguage) {
        return false;
      }

      if (minVal !== null && !isNaN(minVal) && card.price_num < minVal) {
        return false;
      }
      if (maxVal !== null && !isNaN(maxVal) && card.price_num > maxVal) {
        return false;
      }

      return true;
    });

    list.sort((a, b) => {
      if (sortBy === 'name_asc') return a.name.localeCompare(b.name);
      if (sortBy === 'name_desc') return b.name.localeCompare(a.name);
      if (sortBy === 'price_asc') return a.price_num - b.price_num;
      if (sortBy === 'price_desc') return b.price_num - a.price_num;
      if (sortBy === 'newest') return b.releaseDate.localeCompare(a.releaseDate);
      return 0;
    });

    return list;
  }, [marketCards, savedCards, onlyWishlistGrid, searchInput, selectedRarity, selectedLanguage, minPrice, maxPrice, sortBy]);

  const myActiveListings = useMemo(() => {
    if (!currentUser) return [];
    return marketCards.filter((card) => card.sellerId === currentUser.id);
  }, [marketCards, currentUser]);

  const hasActiveFilter =
    searchInput.trim() !== '' ||
    selectedRarity !== 'all' ||
    selectedLanguage !== 'all' ||
    minPrice !== '' ||
    maxPrice !== '' ||
    onlyWishlistGrid ||
    sortBy !== 'name_asc';

  const handleResetFilters = () => {
    setSearchInput('');
    setSelectedRarity('all');
    setSelectedLanguage('all');
    setSortBy('name_asc');
    setMinPrice('');
    setMaxPrice('');
    setOnlyWishlistGrid(false);
  };

  const totalSavedUsd = useMemo(
    () => savedCards.reduce((sum, item) => sum + (item.price_num || 0), 0),
    [savedCards]
  );

  return (
    <div className="mk-wrapper">
      
      {/* AREA CHECKERBOARD KUNING (PENCARIAN & TOMBOL AKSI PASAR) */}
      <div className="mk-search-section">
        <div className="mk-search-container">
          <form className="mk-search-box" onSubmit={(e) => e.preventDefault()}>
            <input 
              type="text" 
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Cari kartu organik, kode set, kota, atau nama pelapak..."
              className="mk-search-input"
            />
            <button type="submit" className="mk-search-icon" title="Cari">
              <SearchIcon />
            </button>
          </form>

          {/* Kelompok Tombol Aksi Kanan: Akun/Login, Jual Kartu, Saved Items, dan Cart */}
          <div className="mk-header-actions">
            {currentUser ? (
              <button
                type="button"
                className="mk-user-btn logged-in"
                onClick={() => handleOpenAccountModal('profile')}
                title="Kelola Identitas Toko, Listing Saya, dan Pesanan"
              >
                <UserIcon />
                <span>{currentUser.storeName}</span>
              </button>
            ) : (
              <button
                type="button"
                className="mk-user-btn"
                onClick={() => {
                  setPendingAction(null);
                  setAuthError('');
                  setAuthTab('login');
                  setIsAuthModalOpen(true);
                }}
              >
                <UserIcon />
                <span>Masuk / Daftar</span>
              </button>
            )}

            <button
              type="button"
              className="mk-sell-listing-btn"
              onClick={handleOpenSellModal}
            >
              <PlusIcon />
              <span>Jual Kartu</span>
            </button>

            <button
              type="button"
              className="mk-saved-btn"
              onClick={() => setActiveDrawer('saved')}
            >
              <span>Saved ({savedCards.length})</span>
              <div className="mk-bookmark-icon-wrapper">
                <BookmarkIcon className="mk-bookmark-svg" />
              </div>
            </button>

            <button
              type="button"
              className="mk-cart-btn"
              onClick={() => {
                setCheckoutReceipt(null);
                setActiveDrawer('cart');
              }}
            >
              <CartIcon className="mk-cart-svg" />
              <span>Cart ({cartItems.length})</span>
            </button>
          </div>
        </div>
      </div>

      {/* PAPAN UTAMA BIRU GELAP (KONTEN) */}
      <div className="mk-main-board">
        
        {/* Baris Filter */}
        <div className="mk-filter-bar">
          
          {/* SORT BY DROPDOWN */}
          <div className="mk-filter-item">
            <span className="mk-filter-label">Sort by</span>
            <div className="mk-dropdown">
              <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value)}
                className="mk-native-select"
                title="Urutkan Kartu"
              >
                <option value="name_asc">A - Z</option>
                <option value="name_desc">Z - A</option>
                <option value="price_asc">Termurah</option>
                <option value="price_desc">Termahal</option>
                <option value="newest">Rilis Terbaru</option>
              </select>
              <div className="mk-dropdown-icon">
                <ChevronDownIcon />
              </div>
            </div>
          </div>

          {/* RARITY DROPDOWN */}
          <div className="mk-filter-item">
            <span className="mk-filter-label">Rarity</span>
            <div className="mk-dropdown">
              <select 
                value={selectedRarity} 
                onChange={(e) => setSelectedRarity(e.target.value)}
                className="mk-native-select"
                title="Filter Kelangkaan"
              >
                <option value="all">Semua Rarity</option>
                <option value="Common">Common</option>
                <option value="Uncommon">Uncommon</option>
                <option value="Reverse Holo">Reverse Holo</option>
                <option value="Rare">Rare</option>
                <option value="Ultra Rare">Ultra Rare</option>
              </select>
              <div className="mk-dropdown-icon">
                <ChevronDownIcon />
              </div>
            </div>
          </div>

          {/* LANGUAGE FILTER INTERAKTIF */}
          <div className="mk-filter-item">
            <span className="mk-filter-label">Language</span>
            <div className="mk-flags-container">
              {['EN', 'ID', 'JP'].map((lang) => {
                const isActive = selectedLanguage === lang;
                return (
                  <button
                    key={lang}
                    type="button"
                    className={`mk-flag-circle ${isActive ? 'active-flag' : ''}`}
                    onClick={() => setSelectedLanguage(isActive ? 'all' : lang)}
                    title={`Filter bahasa ${lang} (klik ulang untuk semua bahasa)`}
                  >
                    <FlagBadge lang={lang} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* INPUT RENTANG HARGA USD */}
          <div className="mk-price-inputs">
            <input 
              type="number" 
              step="any"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="$ min" 
              className="mk-price-input" 
              title="Harga minimum (USD)"
            />
            <span className="mk-price-separator">-</span>
            <input 
              type="number" 
              step="any"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="$ max" 
              className="mk-price-input" 
              title="Harga maksimum (USD)"
            />
            {hasActiveFilter && (
              <button 
                type="button" 
                className="mk-reset-btn"
                onClick={handleResetFilters}
                title="Reset Semua Filter"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Banner aktif jika sedang memfilter khusus Wishlist */}
        {onlyWishlistGrid && (
          <div className="mk-wishlist-filter-banner">
            <span>Menampilkan kartu dari Saved Items Anda ({filteredCards.length} kartu)</span>
            <button type="button" onClick={() => setOnlyWishlistGrid(false)}>
              Tampilkan Semua Listing
            </button>
          </div>
        )}

        {/* STATUS KOSONG ATAU GRID KARTU */}
        {filteredCards.length === 0 ? (
          <div className="mk-empty-state">
            <p className="mk-empty-title">Tidak ada kartu yang cocok</p>
            <p className="mk-empty-desc">
              Tidak ditemukan listing kartu organik untuk filter yang dipilih. Klik tombol Reset untuk menampilkan seluruh kartu.
            </p>
            <button type="button" className="mk-reset-btn mk-empty-reset" onClick={handleResetFilters}>
              Reset Filter
            </button>
          </div>
        ) : (
          <div className="mk-grid">
            {filteredCards.map((card) => {
              const rarityMeta = getRarityMeta(card.rarityText);
              const saved = isCardSaved(card.id);
              const inCart = isCardInCart(card.id);
              const isOwnCard = currentUser && card.sellerId === currentUser.id;
              const displayPrice = `$ ${card.price_num.toFixed(2)}`;

              return (
                <div
                  key={card.id}
                  className="mk-card"
                  onClick={() => {
                    setRevealSellerPhone(false);
                    setSelectedCard(card);
                  }}
                >
                  {/* Pita / Tombol Bookmark Interaktif */}
                  <button 
                    type="button"
                    className={`mk-bookmark-ribbon ${saved ? 'is-saved' : 'not-saved'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSaveCard(card);
                    }}
                    title={saved ? 'Hapus dari Saved Items' : 'Simpan ke Saved Items'}
                  >
                    <BookmarkIcon className="mk-bookmark-svg-white" />
                  </button>

                  {/* Gambar Kartu Fisik Organik */}
                  <div className="mk-card-img-box">
                    <img 
                      src={card.image} 
                      alt={card.name} 
                      className="mk-card-img" 
                      loading="lazy"
                    />
                  </div>

                  {/* Informasi Kartu */}
                  <div className="mk-card-content">
                    <div className="mk-card-row-1">
                      <span className="mk-card-title" title={card.name}>{card.name}</span>
                      <span className="mk-card-price">{displayPrice}</span>
                    </div>
                    <div className="mk-card-row-2">
                      <span className="mk-card-rarity" title={`${card.sellerName} (${card.sellerCity})`}>
                        {card.conditionCode} • {card.sellerName}
                      </span>
                      <div className="mk-dotted-line"></div>
                      <FlagBadge lang={card.language} />
                    </div>
                    <div className="mk-card-row-3">
                      <div className="mk-symbol-group">
                        <RarityIcon type={rarityMeta.symbol} />
                        <span className="mk-card-abbr">{rarityMeta.abbr}</span>
                        <span className="mk-card-set">{card.set}</span>
                      </div>

                      {isOwnCard ? (
                        <span className="mk-own-badge">Toko Anda</span>
                      ) : (
                        <button
                          type="button"
                          className={`mk-card-cart-btn ${inCart ? 'in-cart' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleCartItem(card);
                          }}
                          title={inCart ? 'Hapus dari Keranjang' : 'Tambah ke Keranjang'}
                        >
                          {inCart ? 'Di Cart' : '+ Cart'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>

      {/* =========================================
          MODAL 1: DETAIL LISTING & IDENTITAS PENJUAL
          ========================================= */}
      {selectedCard && createPortal(
        <div 
          className={`mk-modal-overlay ${isClosingModal ? 'closing' : ''}`} 
          onClick={handleCloseModal}
        >
          <div 
            className={`mk-modal-card ${isClosingModal ? 'closing' : ''}`} 
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mk-modal-header">
              <div>
                <span className="mk-modal-subtitle">{selectedCard.setName} ({selectedCard.set}) • #{selectedCard.cardNumber}</span>
                <h2 className="mk-modal-title">{selectedCard.name}</h2>
              </div>
              <button
                type="button"
                className="mk-drawer-close-btn"
                onClick={handleCloseModal}
                title="Tutup Detail"
              >
                <CloseIcon />
              </button>
            </div>

            <div className="mk-modal-body">
              <div className="mk-modal-photo-col">
                <div className="mk-modal-photo-box">
                  <img
                    src={selectedCard.image}
                    alt={selectedCard.name}
                    className="mk-modal-photo"
                  />
                </div>
              </div>

              <div className="mk-modal-details">
                <div className="mk-modal-price-block">
                  <div>
                    <span className="mk-modal-price-label">Harga Jual Pelapak</span>
                    <div className="mk-modal-price-usd">$ {selectedCard.price_num.toFixed(2)}</div>
                    <div className="mk-modal-price-idr">{formatIdr(selectedCard.price_num)}</div>
                  </div>
                  <div className="mk-modal-ref-block">
                    <span className="mk-modal-price-label">Harga Pasar Referensi</span>
                    <div className="mk-modal-ref-usd">$ {selectedCard.marketRefUsd.toFixed(2)}</div>
                    <div className="mk-modal-price-idr">{formatIdr(selectedCard.marketRefUsd)}</div>
                  </div>
                </div>

                <div className="mk-modal-spec-grid">
                  <div className="mk-spec-item">
                    <span className="mk-spec-label">Kondisi Fisik</span>
                    <span className="mk-spec-val">{selectedCard.condition} ({selectedCard.conditionCode})</span>
                  </div>
                  <div className="mk-spec-item">
                    <span className="mk-spec-label">Kelangkaan & Bahasa</span>
                    <span className="mk-spec-val">{selectedCard.rarityText} ({selectedCard.language})</span>
                  </div>
                </div>

                {/* Kotak Identitas Penjual Lengkap */}
                <div className="mk-seller-identity-box">
                  <div className="mk-seller-id-header">
                    <div>
                      <span className="mk-spec-label">Identitas Penjual</span>
                      <h4 className="mk-seller-store-title">{selectedCard.sellerName}</h4>
                      <span className="mk-seller-owner-sub">
                        Pemilik: <strong>{selectedCard.sellerOwner || 'Pelapak Terdaftar'}</strong> • Kota {selectedCard.sellerCity}
                      </span>
                    </div>
                    <span className="mk-seller-joined-tag">
                      Sejak {selectedCard.sellerJoined || '2024'}
                    </span>
                  </div>

                  <div className="mk-seller-contact-bar">
                    <div className="mk-seller-phone-info">
                      <span className="mk-spec-label">Nomor Telepon / WhatsApp</span>
                      <strong>
                        {revealSellerPhone
                          ? selectedCard.sellerPhone || '-'
                          : maskPhoneNumber(selectedCard.sellerPhone)}
                      </strong>
                    </div>
                    <div className="mk-seller-contact-btns">
                      <button
                        type="button"
                        className="mk-btn-outline-sm"
                        onClick={() => setRevealSellerPhone((prev) => !prev)}
                      >
                        {revealSellerPhone ? 'Sembunyikan' : 'Lihat Nomor'}
                      </button>
                      {selectedCard.sellerPhone && (
                        <a
                          href={`https://wa.me/${selectedCard.sellerPhone.replace(/^0/, '62').replace(/\D/g, '')}?text=${encodeURIComponent(
                            `Halo ${selectedCard.sellerName}, apakah kartu ${selectedCard.name} (${selectedCard.set} #${selectedCard.cardNumber}) masih tersedia di Regokemon Marketplace?`
                          )}`}
                          target="_blank"
                          rel="noreferrer"
                          className="mk-btn-wa-sm"
                        >
                          Hubungi WhatsApp
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                <div className="mk-modal-note-box">
                  <span className="mk-spec-label">Catatan Kondisi & Pengiriman Pelapak</span>
                  <p>{selectedCard.sellerNote}</p>
                </div>

                {currentUser && selectedCard.sellerId === currentUser.id ? (
                  <div className="mk-modal-actions-row">
                    <div className="mk-own-listing-notice">
                      Ini adalah listing kartu milik toko Anda ({currentUser.storeName}).
                    </div>
                    <button
                      type="button"
                      className="mk-btn-danger"
                      onClick={() => handleDeleteListing(selectedCard.id)}
                    >
                      Hapus Listing
                    </button>
                  </div>
                ) : (
                  <div className="mk-modal-actions-row">
                    <button
                      type="button"
                      className={`mk-modal-cart-cta ${isCardInCart(selectedCard.id) ? 'in-cart' : ''}`}
                      onClick={() => toggleCartItem(selectedCard)}
                    >
                      <CartIcon className="mk-modal-btn-icon" />
                      <span>
                        {isCardInCart(selectedCard.id)
                          ? 'Sudah di Keranjang'
                          : `Masukkan Keranjang • ${formatIdr(selectedCard.price_num)}`}
                      </span>
                    </button>

                    <button
                      type="button"
                      className={`mk-modal-save-btn ${isCardSaved(selectedCard.id) ? 'saved' : ''}`}
                      onClick={() => toggleSaveCard(selectedCard)}
                      title="Simpan ke Saved Items"
                    >
                      <BookmarkIcon className="mk-modal-btn-icon" />
                      <span>{isCardSaved(selectedCard.id) ? 'Tersimpan' : 'Wishlist'}</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* =========================================
          MODAL 2: JUAL KARTU (TERHUBUNG KE AKUN LOGIN)
          ========================================= */}
      {isSellModalOpen && currentUser && createPortal(
        <div className="mk-modal-overlay" onClick={() => setIsSellModalOpen(false)}>
          <div className="mk-modal-card mk-sell-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="mk-modal-header">
              <div>
                <h2 className="mk-modal-title">Jual Kartu ke Marketplace</h2>
              </div>
              <button
                type="button"
                className="mk-drawer-close-btn"
                onClick={() => setIsSellModalOpen(false)}
                title="Tutup Form"
              >
                <CloseIcon />
              </button>
            </div>

            <form className="mk-sell-body" onSubmit={handleSubmitSellForm}>
              {/* Kolom Kiri: Upload Foto Kartu Fisik */}
              <div className="mk-sell-photo-col">
                <span className="mk-field-label">Foto Fisik Kartu *</span>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                />

                <div
                  className={`mk-upload-dropzone ${sellForm.photoPreview ? 'has-photo' : ''}`}
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                >
                  {sellForm.photoPreview ? (
                    <img
                      src={sellForm.photoPreview}
                      alt="Preview Kartu"
                      className="mk-upload-preview-img"
                    />
                  ) : (
                    <div className="mk-upload-placeholder">
                      <UploadPhotoIcon />
                      <strong>Pilih Foto Kartu dari Perangkat</strong>
                      <span>Format JPG, PNG, atau WEBP</span>
                    </div>
                  )}
                </div>

                {sellForm.photoPreview && (
                  <button
                    type="button"
                    className="mk-change-photo-btn"
                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                  >
                    Ganti Foto Kartu
                  </button>
                )}
              </div>

              {/* Kolom Kanan: Identitas Pelapak Aktif & Spesifikasi Kartu */}
              <div className="mk-sell-fields-col">
                {/* Kartu Identitas Penjual Otomatis dari Akun Login */}
                <div className="mk-active-seller-banner">
                  <div>
                    <span className="mk-spec-label">Identitas Penjual</span>
                    <strong>{currentUser.storeName} ({currentUser.fullName})</strong>
                    <span>{currentUser.phone} • {currentUser.city}</span>
                  </div>
                  <button
                    type="button"
                    className="mk-link-btn"
                    onClick={() => {
                      setIsSellModalOpen(false);
                      handleOpenAccountModal('profile');
                    }}
                  >
                    Ubah Identitas
                  </button>
                </div>

                {sellError && <div className="mk-sell-error">{sellError}</div>}

                <div className="mk-field-row-2">
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="sell-name">Nama Kartu *</label>
                    <input
                      id="sell-name"
                      type="text"
                      className="mk-text-input"
                      value={sellForm.name}
                      onChange={(e) => setSellForm({ ...sellForm, name: e.target.value })}
                    />
                  </div>
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="sell-number">Nomor Kartu</label>
                    <input
                      id="sell-number"
                      type="text"
                      className="mk-text-input"
                      placeholder="116/191"
                      value={sellForm.cardNumber}
                      onChange={(e) => setSellForm({ ...sellForm, cardNumber: e.target.value })}
                    />
                  </div>
                </div>

                <div className="mk-field-row-3">
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="sell-set">Kode Set</label>
                    <input
                      id="sell-set"
                      type="text"
                      className="mk-text-input"
                      placeholder="SSP"
                      value={sellForm.set}
                      onChange={(e) => setSellForm({ ...sellForm, set: e.target.value })}
                    />
                  </div>
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="sell-rarity">Rarity</label>
                    <select
                      id="sell-rarity"
                      className="mk-text-input"
                      value={sellForm.rarityText}
                      onChange={(e) => setSellForm({ ...sellForm, rarityText: e.target.value })}
                    >
                      <option value="Common">Common</option>
                      <option value="Uncommon">Uncommon</option>
                      <option value="Reverse Holo">Reverse Holo</option>
                      <option value="Rare">Rare</option>
                      <option value="Ultra Rare">Ultra Rare</option>
                    </select>
                  </div>
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="sell-lang">Bahasa</label>
                    <select
                      id="sell-lang"
                      className="mk-text-input"
                      value={sellForm.language}
                      onChange={(e) => setSellForm({ ...sellForm, language: e.target.value })}
                    >
                      <option value="EN">EN (English)</option>
                      <option value="ID">ID (Indonesia)</option>
                      <option value="JP">JP (Japanese)</option>
                    </select>
                  </div>
                </div>

                {/* Pilihan Kondisi Fisik Kartu (Tombol Segmented Standar TCG) */}
                <div className="mk-field-group">
                  <span className="mk-field-label">Kondisi Fisik Kartu (Standar TCG) *</span>
                  <div className="mk-condition-segmented">
                    {CONDITION_OPTIONS.map((opt) => {
                      const active = sellForm.conditionCode === opt.code;
                      return (
                        <button
                          key={opt.code}
                          type="button"
                          className={`mk-cond-seg-btn ${active ? 'active' : ''}`}
                          onClick={() => setSellForm({ ...sellForm, conditionCode: opt.code })}
                        >
                          <strong>{opt.code}</strong>
                          <span>{opt.label}</span>
                        </button>
                      );
                    })}
                  </div>
                  <span className="mk-cond-helper">
                    {CONDITION_OPTIONS.find((c) => c.code === sellForm.conditionCode)?.desc}
                  </span>
                </div>

                {/* Harga Jual USD & Konversi Otomatis IDR */}
                <div className="mk-field-row-2">
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="sell-price">Harga Jual (USD) *</label>
                    <input
                      id="sell-price"
                      type="number"
                      step="0.05"
                      min="0.1"
                      className="mk-text-input"
                      placeholder="0.00"
                      value={sellForm.priceUsd}
                      onChange={(e) => setSellForm({ ...sellForm, priceUsd: e.target.value })}
                    />
                  </div>
                  <div className="mk-field-group">
                    <span className="mk-field-label">Estimasi Rupiah Diterima</span>
                    <div className="mk-idr-preview-box">
                      {sellForm.priceUsd && !isNaN(parseFloat(sellForm.priceUsd))
                        ? formatIdr(parseFloat(sellForm.priceUsd))
                        : 'Rp 0'}
                    </div>
                  </div>
                </div>

                <div className="mk-field-group">
                  <label className="mk-field-label" htmlFor="sell-note">Catatan Kondisi & Pengiriman</label>
                  <textarea
                    id="sell-note"
                    rows={2}
                    className="mk-text-input mk-textarea"
                    value={sellForm.sellerNote}
                    onChange={(e) => setSellForm({ ...sellForm, sellerNote: e.target.value })}
                  />
                </div>

                <div className="mk-sell-footer-btns">
                  <button
                    type="button"
                    className="mk-btn-secondary"
                    onClick={() => setIsSellModalOpen(false)}
                  >
                    Batal
                  </button>
                  <button type="submit" className="mk-btn-primary">
                    Tayangkan Listing
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* =========================================
          MODAL 3: LOGIN & REGISTRASI AKUN
          ========================================= */}
      {isAuthModalOpen && createPortal(
        <div className="mk-modal-overlay" onClick={() => setIsAuthModalOpen(false)}>
          <div className="mk-modal-card mk-auth-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="mk-modal-header">
              <div>
                <h2 className="mk-modal-title">
                  {authTab === 'login' ? 'Masuk ke Marketplace' : 'Daftar Akun Baru'}
                </h2>
              </div>
              <button
                type="button"
                className="mk-drawer-close-btn"
                onClick={() => setIsAuthModalOpen(false)}
                title="Tutup"
              >
                <CloseIcon />
              </button>
            </div>

            <div className="mk-auth-tabs">
              <button
                type="button"
                className={`mk-auth-tab-btn ${authTab === 'login' ? 'active' : ''}`}
                onClick={() => {
                  setAuthError('');
                  setAuthTab('login');
                }}
              >
                Masuk Akun
              </button>
              <button
                type="button"
                className={`mk-auth-tab-btn ${authTab === 'register' ? 'active' : ''}`}
                onClick={() => {
                  setAuthError('');
                  setAuthTab('register');
                }}
              >
                Daftar Baru
              </button>
            </div>

            <div className="mk-auth-body">
              {authError && <div className="mk-sell-error">{authError}</div>}

              {authTab === 'login' ? (
                <form className="mk-auth-form" onSubmit={handleLoginSubmit}>
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="login-id">Email / Nomor WhatsApp / Nama Toko</label>
                    <input
                      id="login-id"
                      type="text"
                      className="mk-text-input"
                      value={loginForm.identifier}
                      onChange={(e) => setLoginForm({ ...loginForm, identifier: e.target.value })}
                    />
                  </div>
                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="login-pass">Kata Sandi</label>
                    <input
                      id="login-pass"
                      type="password"
                      className="mk-text-input"
                      value={loginForm.password}
                      onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                    />
                  </div>

                  <button type="submit" className="mk-btn-primary mk-full-btn">
                    Masuk Akun
                  </button>
                </form>
              ) : (
                <form className="mk-auth-form" onSubmit={handleRegisterSubmit}>
                  <div className="mk-field-row-2">
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="reg-fullname">Nama Lengkap *</label>
                      <input
                        id="reg-fullname"
                        type="text"
                        className="mk-text-input"
                        value={registerForm.fullName}
                        onChange={(e) => setRegisterForm({ ...registerForm, fullName: e.target.value })}
                      />
                    </div>
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="reg-store">Nama Toko *</label>
                      <input
                        id="reg-store"
                        type="text"
                        className="mk-text-input"
                        value={registerForm.storeName}
                        onChange={(e) => setRegisterForm({ ...registerForm, storeName: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="mk-field-row-2">
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="reg-phone">Nomor HP / WhatsApp *</label>
                      <input
                        id="reg-phone"
                        type="tel"
                        className="mk-text-input"
                        placeholder="08xxxxxxxxxx"
                        value={registerForm.phone}
                        onChange={(e) => setRegisterForm({ ...registerForm, phone: e.target.value })}
                      />
                    </div>
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="reg-city">Kota Pengiriman *</label>
                      <input
                        id="reg-city"
                        type="text"
                        className="mk-text-input"
                        value={registerForm.city}
                        onChange={(e) => setRegisterForm({ ...registerForm, city: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="mk-field-row-2">
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="reg-email">Alamat Email</label>
                      <input
                        id="reg-email"
                        type="email"
                        className="mk-text-input"
                        placeholder="nama@email.com"
                        value={registerForm.email}
                        onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                      />
                    </div>
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="reg-pass">Kata Sandi *</label>
                      <input
                        id="reg-pass"
                        type="password"
                        className="mk-text-input"
                        value={registerForm.password}
                        onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="reg-addr">Alamat Lengkap</label>
                    <input
                      id="reg-addr"
                      type="text"
                      className="mk-text-input"
                      value={registerForm.address}
                      onChange={(e) => setRegisterForm({ ...registerForm, address: e.target.value })}
                    />
                  </div>

                  <button type="submit" className="mk-btn-primary mk-full-btn">
                    Daftar & Masuk
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* =========================================
          MODAL 4: PANEL AKUN, LISTING SAYA & PESANAN
          ========================================= */}
      {isAccountModalOpen && currentUser && createPortal(
        <div className="mk-modal-overlay" onClick={() => setIsAccountModalOpen(false)}>
          <div className="mk-modal-card mk-account-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="mk-modal-header">
              <div>
                <h2 className="mk-modal-title">{currentUser.storeName} ({currentUser.fullName})</h2>
              </div>
              <button
                type="button"
                className="mk-drawer-close-btn"
                onClick={() => setIsAccountModalOpen(false)}
                title="Tutup Panel Akun"
              >
                <CloseIcon />
              </button>
            </div>

            <div className="mk-auth-tabs">
              <button
                type="button"
                className={`mk-auth-tab-btn ${accountTab === 'profile' ? 'active' : ''}`}
                onClick={() => setAccountTab('profile')}
              >
                Identitas Penjual
              </button>
              <button
                type="button"
                className={`mk-auth-tab-btn ${accountTab === 'listings' ? 'active' : ''}`}
                onClick={() => setAccountTab('listings')}
              >
                Listing Saya ({myActiveListings.length})
              </button>
              <button
                type="button"
                className={`mk-auth-tab-btn ${accountTab === 'orders' ? 'active' : ''}`}
                onClick={() => setAccountTab('orders')}
              >
                Pesanan Saya ({orderHistory.length})
              </button>
            </div>

            <div className="mk-auth-body">
              {accountTab === 'profile' && (
                <form className="mk-auth-form" onSubmit={handleSaveProfile}>
                  {profileSavedNotice && (
                    <div className="mk-profile-success">{profileSavedNotice}</div>
                  )}

                  <div className="mk-field-row-2">
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="prof-fullname">Nama Lengkap *</label>
                      <input
                        id="prof-fullname"
                        type="text"
                        className="mk-text-input"
                        value={profileEditForm.fullName}
                        onChange={(e) => setProfileEditForm({ ...profileEditForm, fullName: e.target.value })}
                      />
                    </div>
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="prof-store">Nama Toko *</label>
                      <input
                        id="prof-store"
                        type="text"
                        className="mk-text-input"
                        value={profileEditForm.storeName}
                        onChange={(e) => setProfileEditForm({ ...profileEditForm, storeName: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="mk-field-row-2">
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="prof-phone">Nomor HP / WhatsApp *</label>
                      <input
                        id="prof-phone"
                        type="tel"
                        className="mk-text-input"
                        value={profileEditForm.phone}
                        onChange={(e) => setProfileEditForm({ ...profileEditForm, phone: e.target.value })}
                      />
                    </div>
                    <div className="mk-field-group">
                      <label className="mk-field-label" htmlFor="prof-city">Kota Pengiriman *</label>
                      <input
                        id="prof-city"
                        type="text"
                        className="mk-text-input"
                        value={profileEditForm.city}
                        onChange={(e) => setProfileEditForm({ ...profileEditForm, city: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="prof-email">Alamat Email</label>
                    <input
                      id="prof-email"
                      type="email"
                      className="mk-text-input"
                      value={profileEditForm.email}
                      onChange={(e) => setProfileEditForm({ ...profileEditForm, email: e.target.value })}
                    />
                  </div>

                  <div className="mk-field-group">
                    <label className="mk-field-label" htmlFor="prof-addr">Alamat Lengkap</label>
                    <input
                      id="prof-addr"
                      type="text"
                      className="mk-text-input"
                      value={profileEditForm.address}
                      onChange={(e) => setProfileEditForm({ ...profileEditForm, address: e.target.value })}
                    />
                  </div>

                  <div className="mk-account-footer-row">
                    <button
                      type="button"
                      className="mk-btn-danger-outline"
                      onClick={() => {
                        setCurrentUser(null);
                        setIsAccountModalOpen(false);
                      }}
                    >
                      Keluar Akun (Logout)
                    </button>
                    <button type="submit" className="mk-btn-primary">
                      Simpan Perubahan Identitas
                    </button>
                  </div>
                </form>
              )}

              {accountTab === 'listings' && (
                <div className="mk-account-list-section">
                  {myActiveListings.length === 0 ? (
                    <div className="mk-account-empty">
                      <p>Anda belum menayangkan listing kartu untuk dijual.</p>
                      <button
                        type="button"
                        className="mk-btn-primary"
                        onClick={() => {
                          setIsAccountModalOpen(false);
                          setIsSellModalOpen(true);
                        }}
                      >
                        Pasang Listing Kartu Pertama
                      </button>
                    </div>
                  ) : (
                    myActiveListings.map((item) => (
                      <div key={item.id} className="mk-account-item-row">
                        <img src={item.image} alt={item.name} className="mk-account-item-thumb" />
                        <div className="mk-account-item-info">
                          <strong>{item.name} ({item.set} #{item.cardNumber})</strong>
                          <span>Kondisi: {item.condition} ({item.conditionCode})</span>
                          <span className="mk-account-item-price">
                            $ {item.price_num.toFixed(2)} ({formatIdr(item.price_num)})
                          </span>
                        </div>
                        <button
                          type="button"
                          className="mk-btn-danger-outline"
                          onClick={() => handleDeleteListing(item.id)}
                        >
                          Hapus
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}

              {accountTab === 'orders' && (
                <div className="mk-account-list-section">
                  {orderHistory.length === 0 ? (
                    <div className="mk-account-empty">
                      <p>Belum ada riwayat pembelian kartu.</p>
                    </div>
                  ) : (
                    orderHistory.map((ord) => (
                      <div key={ord.orderId} className="mk-order-history-card">
                        <div className="mk-order-card-head">
                          <strong>Pesanan #{ord.orderId}</strong>
                          <span>{ord.createdAt} • {ord.paymentMethod}</span>
                        </div>
                        <div className="mk-order-card-sub">
                          Penerima: {ord.buyerName} ({ord.buyerPhone}) • {ord.courier}
                        </div>
                        <div className="mk-order-card-items">
                          {ord.items.map((it) => (
                            <div key={it.id} className="mk-receipt-row">
                              <span>{it.name} ({it.sellerName})</span>
                              <strong>$ {it.price_num.toFixed(2)}</strong>
                            </div>
                          ))}
                        </div>
                        <div className="mk-order-card-foot">
                          <span>Total Dibayar</span>
                          <strong>$ {ord.totalUsd.toFixed(2)} ({ord.totalIdr})</strong>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* =========================================
          UI SIDE DRAWER: SAVED ITEMS & SHOPPING CART
          ========================================= */}
      {createPortal(
        <>
          <div 
            className={`mk-drawer-overlay ${activeDrawer ? 'open' : ''}`} 
            onClick={() => setActiveDrawer(null)}
          ></div>

      {/* DRAWER 1: SAVED ITEMS / WISHLIST */}
      <div className={`mk-saved-drawer ${activeDrawer === 'saved' ? 'open' : ''}`}>
        <div className="mk-drawer-header">
          <div className="mk-drawer-title-group">
            <div className="mk-drawer-icon">
              <BookmarkIcon className="w-full h-full" />
            </div>
            <h2>Saved Items</h2>
            <span className="mk-drawer-count">{savedCards.length}</span>
          </div>
          <button 
            type="button" 
            className="mk-drawer-close-btn" 
            onClick={() => setActiveDrawer(null)}
            title="Tutup Panel"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="mk-drawer-content">
          {savedCards.length > 0 ? (
            savedCards.map((item) => {
              const displayItemPrice = `$ ${(item.price_num || 0).toFixed(2)}`;
              return (
                <div
                  key={item.id}
                  className="mk-drawer-item"
                  onClick={() => {
                    setActiveDrawer(null);
                    setRevealSellerPhone(false);
                    setSelectedCard(item);
                  }}
                >
                  <div className="mk-drawer-item-img-box">
                    <img 
                      src={item.image || '/card-result.png'} 
                      alt={item.name} 
                      className="mk-drawer-item-img" 
                    />
                  </div>
                  <div className="mk-drawer-item-info">
                    <span className="mk-drawer-item-name" title={item.name}>{item.name}</span>
                    <span className="mk-drawer-item-desc">
                      {item.condition || 'Near Mint'} • {item.sellerName}
                    </span>
                    <div className="mk-drawer-price-row">
                      <span className="mk-drawer-item-price">{displayItemPrice}</span>
                      <span className="mk-drawer-item-idr">{formatIdr(item.price_num)}</span>
                    </div>
                  </div>
                  <div className="mk-drawer-item-actions">
                    <button
                      type="button"
                      className="mk-drawer-move-cart-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        moveSavedToCart(item);
                      }}
                      title="Masukkan ke Keranjang"
                    >
                      + Cart
                    </button>
                    <button 
                      type="button"
                      className="mk-drawer-remove-btn" 
                      onClick={(e) => {
                        e.stopPropagation();
                        removeSavedCard(item.id);
                      }}
                      title="Hapus dari tersimpan"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="mk-drawer-empty">
              <p>Belum ada kartu yang disimpan.</p>
              <span>Klik ikon pita bookmark pada kartu untuk menyimpannya di sini.</span>
            </div>
          )}
        </div>

        <div className="mk-drawer-footer">
          {savedCards.length > 0 && (
            <div className="mk-drawer-summary-box">
              <span>Total Estimasi ({savedCards.length} kartu)</span>
              <div className="mk-drawer-summary-Right">
                <strong>$ {totalSavedUsd.toFixed(2)}</strong>
                <span>{formatIdr(totalSavedUsd)}</span>
              </div>
            </div>
          )}
          <div className="mk-drawer-footer-stack">
            <button 
              type="button" 
              className="mk-drawer-action-btn"
              disabled={savedCards.length === 0}
              onClick={() => {
                setOnlyWishlistGrid(true);
                setActiveDrawer(null);
              }}
            >
              Tampilkan Wishlist di Grid ({savedCards.length})
            </button>
            {savedCards.length > 0 && (
              <button
                type="button"
                className="mk-drawer-secondary-btn"
                onClick={clearSavedCards}
              >
                Kosongkan Saved Items
              </button>
            )}
          </div>
        </div>
      </div>

      {/* DRAWER 2: SHOPPING CART (KERANJANG BELANJA & PENGIRIMAN) */}
      <div className={`mk-saved-drawer ${activeDrawer === 'cart' ? 'open' : ''}`}>
        <div className="mk-drawer-header">
          <div className="mk-drawer-title-group">
            <div className="mk-drawer-icon">
              <CartIcon className="w-full h-full" />
            </div>
            <h2>Shopping Cart</h2>
            <span className="mk-drawer-count">{cartItems.length}</span>
          </div>
          <button 
            type="button" 
            className="mk-drawer-close-btn" 
            onClick={() => setActiveDrawer(null)}
            title="Tutup Keranjang"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="mk-drawer-content">
          {checkoutReceipt ? (
            <div className="mk-checkout-receipt">
              <span className="mk-receipt-badge">Pesanan Berhasil Dibuat</span>
              <h3>Nomor Pesanan #{checkoutReceipt.orderId}</h3>
              <p>
                Penerima: <strong>{checkoutReceipt.buyerName}</strong> ({checkoutReceipt.buyerPhone})<br />
                Alamat: {checkoutReceipt.shippingAddress}<br />
                Layanan: {checkoutReceipt.courier} ({checkoutReceipt.paymentMethod})
              </p>
              <div className="mk-receipt-list">
                {checkoutReceipt.items.map((it) => (
                  <div key={it.id} className="mk-receipt-row">
                    <span>{it.name} ({it.sellerName})</span>
                    <strong>$ {it.price_num.toFixed(2)}</strong>
                  </div>
                ))}
              </div>
              <div className="mk-receipt-total">
                <span>Total Pembayaran</span>
                <div>
                  <strong>$ {checkoutReceipt.totalUsd.toFixed(2)}</strong>
                  <span>{checkoutReceipt.totalIdr}</span>
                </div>
              </div>
              <button
                type="button"
                className="mk-drawer-action-btn"
                onClick={() => {
                  setCheckoutReceipt(null);
                  setActiveDrawer(null);
                }}
              >
                Selesai
              </button>
            </div>
          ) : cartItems.length > 0 ? (
            <>
              {cartItems.map((item) => (
                <div
                  key={item.id}
                  className="mk-drawer-item"
                  onClick={() => {
                    setActiveDrawer(null);
                    setRevealSellerPhone(false);
                    setSelectedCard(item);
                  }}
                >
                  <div className="mk-drawer-item-img-box">
                    <img 
                      src={item.image || '/card-result.png'} 
                      alt={item.name} 
                      className="mk-drawer-item-img" 
                    />
                  </div>
                  <div className="mk-drawer-item-info">
                    <span className="mk-drawer-item-name" title={item.name}>{item.name}</span>
                    <span className="mk-drawer-item-desc">
                      {item.sellerName} • {item.sellerCity}
                    </span>
                    <div className="mk-drawer-price-row">
                      <span className="mk-drawer-item-price">$ {(item.price_num || 0).toFixed(2)}</span>
                      <span className="mk-drawer-item-idr">{formatIdr(item.price_num)}</span>
                    </div>
                  </div>
                  <button 
                    type="button"
                    className="mk-drawer-remove-btn" 
                    onClick={(e) => {
                      e.stopPropagation();
                      removeCartItem(item.id);
                    }}
                    title="Hapus dari keranjang"
                  >
                    <TrashIcon />
                  </button>
                </div>
              ))}

              {/* Opsi Pengiriman & Metode Pembayaran */}
              <div className="mk-cart-shipping-box">
                <div className="mk-field-group">
                  <label className="mk-field-label" htmlFor="cart-courier">Pilih Layanan Pengiriman</label>
                  <select
                    id="cart-courier"
                    className="mk-text-input"
                    value={selectedCourier}
                    onChange={(e) => setSelectedCourier(e.target.value)}
                  >
                    <option value="reguler">Reguler Toploader Box ($ 0.45)</option>
                    <option value="ekspres">Safe Express Bergaransi ($ 0.85)</option>
                  </select>
                </div>

                <div className="mk-field-group">
                  <label className="mk-field-label" htmlFor="cart-pay">Metode Pembayaran</label>
                  <select
                    id="cart-pay"
                    className="mk-text-input"
                    value={selectedPayment}
                    onChange={(e) => setSelectedPayment(e.target.value)}
                  >
                    <option value="QRIS">QRIS Instan</option>
                    <option value="Virtual Account BCA">Virtual Account BCA</option>
                    <option value="Virtual Account Mandiri">Virtual Account Mandiri</option>
                  </select>
                </div>
              </div>
            </>
          ) : (
            <div className="mk-drawer-empty">
              <p>Keranjang belanja masih kosong.</p>
              <span>Klik tombol + Cart pada kartu yang ingin Anda beli.</span>
            </div>
          )}
        </div>

        {!checkoutReceipt && (
          <div className="mk-drawer-footer">
            {cartItems.length > 0 && (
              <div className="mk-cart-breakdown">
                <div className="mk-breakdown-row">
                  <span>Subtotal ({cartItems.length} kartu)</span>
                  <span>$ {subtotalCartUsd.toFixed(2)}</span>
                </div>
                <div className="mk-breakdown-row">
                  <span>Proteksi Sleeve & Toploader</span>
                  <span>$ {protectionFeeUsd.toFixed(2)}</span>
                </div>
                <div className="mk-breakdown-row">
                  <span>Ongkos Kirim</span>
                  <span>$ {courierFeeUsd.toFixed(2)}</span>
                </div>
                <div className="mk-breakdown-total">
                  <span>Total Tagihan</span>
                  <div className="mk-drawer-summary-Right">
                    <strong>$ {totalCartUsd.toFixed(2)}</strong>
                    <span>{formatIdr(totalCartUsd)}</span>
                  </div>
                </div>
              </div>
            )}
            <button 
              type="button" 
              className="mk-drawer-action-btn"
              disabled={cartItems.length === 0}
              onClick={handleCheckoutCart}
            >
              {currentUser
                ? `Checkout Sekarang ${cartItems.length > 0 ? `(${formatIdr(totalCartUsd)})` : ''}`
                : 'Masuk Akun untuk Checkout'}
            </button>
          </div>
        )}
      </div>
        </>,
        document.body
      )}

    </div>
  );
}
