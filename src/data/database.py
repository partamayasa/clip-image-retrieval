import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
import pandas as pd

from src import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Default Static Configurations to be migrated to SQLite
DEFAULT_SYSTEM_CONFIGS = [
    {
        "key": "clip_model_name",
        "value": "openai/clip-vit-base-patch32",
        "description": "ViT-B/32 shared latent space CLIP model checkpoint",
    },
    {
        "key": "embedding_dim",
        "value": "512",
        "description": "Multimodal latent vector space dimension",
    },
    {
        "key": "batch_size",
        "value": "32",
        "description": "Inference batch size for image encoding",
    },
    {
        "key": "random_seed",
        "value": "42",
        "description": "Deterministic seed for reproducible evaluation splits",
    },
    {
        "key": "app_title",
        "value": "Fashion Multimodal Retrieval Explorer",
        "description": "Web dashboard application title",
    },
    {
        "key": "app_version",
        "value": "1.0.0",
        "description": "Application version",
    },
]

# Default Target Article Types
DEFAULT_TARGET_ARTICLE_TYPES = [
    "Tshirts",
    "Shirts",
    "Casual Shoes",
    "Formal Shoes",
    "Sports Shoes",
    "Watches",
    "Backpacks",
    "Jackets",
    "Jeans",
    "Handbags",
    "Caps",
    "Sunglasses",
]

# 20 Catalog Validation Samples (Appendix A) with full metadata
DEFAULT_AUDIT_SAMPLES = [
    {
        "no": 1,
        "product_id": 1163,
        "product_display_name": "Nike Sahara Team India Fanwear Round Neck Jersey",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Blue",
        "usage": "Sports",
        "image_filename": "1163.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Warna biru dan potongan kerah bulat pada jersey kriket India selaras sepenuhnya dengan anotasi metadata.",
    },
    {
        "no": 2,
        "product_id": 1164,
        "product_display_name": "Nike Men Blue T20 Indian Cricket Jersey",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Blue",
        "usage": "Sports",
        "image_filename": "1164.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Jersey polo kriket berkerah dengan aksen jingga mencolok di bagian pundak terlihat sangat jelas dan konsisten.",
    },
    {
        "no": 3,
        "product_id": 1165,
        "product_display_name": "Nike Mean Team India Cricket Jersey",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Blue",
        "usage": "Sports",
        "image_filename": "1165.jpg",
        "validation_status": "Tidak Konsisten / Masalah Ditemukan",
        "finding_rationale": "Gambar menampilkan kardigan rajut hitam untuk wanita; terdapat diskrepansi fatal terhadap metadata yang mencatat jersey kriket biru pria.",
    },
    {
        "no": 4,
        "product_id": 1525,
        "product_display_name": "Puma Deck Navy Blue Backpack",
        "master_category": "Accessories",
        "article_type": "Backpacks",
        "gender": "Unisex",
        "base_colour": "Navy Blue",
        "usage": "Casual",
        "image_filename": "1525.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Ransel kasual biru tua dengan cetakan tipografi PUMA putih vertikal yang mencolok di bagian depan.",
    },
    {
        "no": 5,
        "product_id": 1526,
        "product_display_name": "Puma Big Cat Backpack Black",
        "master_category": "Accessories",
        "article_type": "Backpacks",
        "gender": "Unisex",
        "base_colour": "Black",
        "usage": "Casual",
        "image_filename": "1526.jpg",
        "validation_status": "Sebagian Konsisten",
        "finding_rationale": "Bentuk ransel hitam dan logo Puma sesuai dengan tampilan visual; label metadata 'usage: Sports' cenderung ambigu untuk ransel kasual harian.",
    },
    {
        "no": 6,
        "product_id": 1528,
        "product_display_name": "Puma Men Ferrari Black Fleece Jacket",
        "master_category": "Apparel",
        "article_type": "Jackets",
        "gender": "Men",
        "base_colour": "Black",
        "usage": "Sports",
        "image_filename": "1528.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Jaket fleece hitam pria bertema Puma Ferrari motorsport dengan ritsleting depan penuh.",
    },
    {
        "no": 7,
        "product_id": 1529,
        "product_display_name": "Ferrari Tee",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Red",
        "usage": "Casual",
        "image_filename": "1529.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Kaus kasual leher bulat merah pria dengan lambang perisai Scuderia Ferrari yang mencolok.",
    },
    {
        "no": 8,
        "product_id": 1530,
        "product_display_name": "Puma Men Ferrari Track Jacket",
        "master_category": "Apparel",
        "article_type": "Jackets",
        "gender": "Men",
        "base_colour": "Red",
        "usage": "Sports",
        "image_filename": "1530.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Jaket training olahraga merah pria dengan aksen garis balap khas Puma Ferrari.",
    },
    {
        "no": 9,
        "product_id": 1531,
        "product_display_name": "Puma Men Grey Solid Round Neck T-Shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Grey",
        "usage": "Casual",
        "image_filename": "1531.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Kaus kasual polos abu-abu pria dengan siluet leher bulat klasik.",
    },
    {
        "no": 10,
        "product_id": 1532,
        "product_display_name": "Puma Men Grey Leaping Cat T-shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Grey",
        "usage": "Casual",
        "image_filename": "1532.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Kaus kasual abu-abu pria dengan cetakan siluet kucing melompat Puma besar di bagian dada.",
    },
    {
        "no": 11,
        "product_id": 1533,
        "product_display_name": "Puma Men Cat Red T-shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Red",
        "usage": "Casual",
        "image_filename": "1533.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Kaus kasual merah pria dengan cetakan siluet kucing Puma putih besar di dada kiri.",
    },
    {
        "no": 12,
        "product_id": 1534,
        "product_display_name": "Puma Men Black Leaping Cat T-shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Black",
        "usage": "Casual",
        "image_filename": "1534.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Kaus kasual hitam polos pria dengan cetakan grafis siluet Puma putih berukuran besar.",
    },
    {
        "no": 13,
        "product_id": 1535,
        "product_display_name": "Puma Unisex Logo Cap",
        "master_category": "Accessories",
        "article_type": "Caps",
        "gender": "Unisex",
        "base_colour": "Black",
        "usage": "Casual",
        "image_filename": "1535.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Topi bisbol hitam unisex dengan bordir logo Puma putih di bagian depan dan panel jaring samping berpori.",
    },
    {
        "no": 14,
        "product_id": 1536,
        "product_display_name": "Puma Men Black Net Jersey",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Black",
        "usage": "Sports",
        "image_filename": "1536.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Jersey atletik hitam polos dengan bordir logo kecil Puma di dada kiri atas dan aksen garis samping halus.",
    },
    {
        "no": 15,
        "product_id": 1537,
        "product_display_name": "Puma Men Red Net Jersey",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Red",
        "usage": "Sports",
        "image_filename": "1537.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Varian warna merah dari model jersey 1536; warna, potongan atletik, dan bahan poliester selaras sempurna dengan metadata.",
    },
    {
        "no": 16,
        "product_id": 1538,
        "product_display_name": "Puma Men Ferrari Track Black T-shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Blue",
        "usage": "Casual",
        "image_filename": "1538.jpg",
        "validation_status": "Sebagian Konsisten",
        "finding_rationale": "Kontradiksi tekstual: productDisplayName mencantumkan 'Black T-shirt', namun atribut baseColour terindeks sebagai 'Blue'.",
    },
    {
        "no": 17,
        "product_id": 1539,
        "product_display_name": "Puma Men Ferrari Grey T-shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Grey",
        "usage": "Casual",
        "image_filename": "1539.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Kaus kasual abu-abu pria Puma Ferrari yang selaras sepenuhnya di seluruh anotasi atribut.",
    },
    {
        "no": 18,
        "product_id": 1540,
        "product_display_name": "Puma Men Ferrari Vintage Black Polo T-shirt",
        "master_category": "Apparel",
        "article_type": "Tshirts",
        "gender": "Men",
        "base_colour": "Blue",
        "usage": "Casual",
        "image_filename": "1540.jpg",
        "validation_status": "Sebagian Konsisten",
        "finding_rationale": "Kontradiksi tekstual: productDisplayName mencantumkan 'Black Polo', namun atribut baseColour terindeks sebagai 'Blue'.",
    },
    {
        "no": 19,
        "product_id": 1541,
        "product_display_name": "Puma Men's Ballistic Spike White Green Shoe",
        "master_category": "Footwear",
        "article_type": "Sports Shoes",
        "gender": "Men",
        "base_colour": "White",
        "usage": "Sports",
        "image_filename": "1541.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Sepatu olahraga kriket bertali putih pria dengan aksen sol berduri hijau.",
    },
    {
        "no": 20,
        "product_id": 1542,
        "product_display_name": "Puma Men's Ballistic Rubber Shoe",
        "master_category": "Footwear",
        "article_type": "Sports Shoes",
        "gender": "Men",
        "base_colour": "White",
        "usage": "Sports",
        "image_filename": "1542.jpg",
        "validation_status": "Konsisten",
        "finding_rationale": "Sepatu olahraga atletik putih pria dengan sol karet sintetis yang tahan lama.",
    },
]

# 5 Key Multimodal Retrieval Insights
DEFAULT_RETRIEVAL_INSIGHTS = [
    {
        "insight_order": 1,
        "topic": "Kaos Oblong Terlalu Banyak, Produk Lain Jadi Susah Muncul",
        "observation": "Koleksi barang di dataset sangat tidak seimbang. Kaos oblong (T-shirts) jumlahnya sangat dominan (257 produk atau lebih dari 17%), sementara barang lain seperti tas ransel (Backpacks) hanya tersedia 31 produk.",
        "retrieval_implication": "Ibarat membuka lemari yang 80% isinya kaos, saat pengguna mencari kata umum seperti 'black t-shirt', sistem langsung kebanjiran puluhan pilihan kaos hitam yang bentuknya mirip. Persaingan di peringkat teratas menjadi sangat padat. Sebaliknya, saat mencari tas atau jaket, pilihannya sedikit dan rentan tertutup oleh produk lain yang populasinya melimpah.",
        "action_solution": "Agar adil, kueri evaluasi dirancang seimbang untuk semua kategori (tidak berat sebelah ke kaos saja) dan sistem diuji pada peringkat bertingkat (Top 5, Top 10, dan Top 20).",
    },
    {
        "insight_order": 2,
        "topic": "Warna Hitam, Putih, dan Biru Sangat Mendominasi",
        "observation": "Hampir separuh isi katalog (lebih dari 46%) hanya berputar di tiga warna netral: Hitam (362 produk), Putih (165 produk), dan Biru (174 produk). Warna unik seperti toska atau peach sangat jarang.",
        "retrieval_implication": "Jika pembeli hanya mengetik kata kunci warna sederhana seperti 'baju hitam kasual', AI akan kebingungan karena di lemari ada tas hitam, sepatu hitam, hingga celana hitam. Kata warna saja tidak cukup bagi AI untuk menebak wujud fisik barang yang diinginkan pembeli.",
        "action_solution": "Kita melatih pencarian dengan format multi-atribut berjenjang (gender + warna + jenis barang + gaya, contoh: 'a men black casual t-shirt') agar AI langsung membidik bentuk fisik produk secara tepat.",
    },
    {
        "insight_order": 3,
        "topic": "Batas Baju Santai dan Baju Olahraga Sering Samar dan Tertukar",
        "observation": "Sebagian besar pakaian (76%) dicap sebagai busana santai (Casual), sedangkan baju olahraga (Sports) hanya 9% dan pakaian formal hanya 5%.",
        "retrieval_implication": "Secara kasat mata, kaos olahraga modern sering kali terlihat persis seperti kaos oblong santai sehari-hari, begitu juga ransel kasual berlogo olahraga. Karena tampilan visualnya tumpang tindih, jika kita hanya mencari kata 'sports', AI rentan salah mengambil kaos santai biasa.",
        "action_solution": "Jangan jadikan kata fungsi/kegunaan sebagai kata kunci utama yang berdiri sendiri. Tempatkan kata gaya pakaian sebagai pelengkap di akhir kueri (contoh: 'sepatu pria warna hitam gaya formal') sehingga AI mendahulukan bentuk fisik barang terlebih dahulu.",
    },
    {
        "insight_order": 4,
        "topic": "Foto Barang Saja Tanpa Model Manusia Bikin AI Ragu Soal Gender",
        "observation": "Banyak produk seperti jam tangan, tas, kacamata, dan sepatu yang difoto terisolasi di atas latar putih bersih tanpa ada sosok manusia atau manekin yang memakainya.",
        "retrieval_implication": "Manusia maupun AI sulit memastikan apakah sebuah jam tangan perak polos atau ransel hitam itu untuk pria atau wanita jika tidak ada orang yang memakainya. Jika pembeli mencari 'jam tangan pria', AI bisa membuang jam tangan yang sebenarnya cocok hanya karena di foto tidak terlihat sosok pria.",
        "action_solution": "Sistem membedakan dua skema uji: untuk pakaian yang ada model manusianya, kata gender disertakan. Namun untuk produk netral seperti tas dan jam tangan, sistem juga menguji pencarian tanpa kata gender agar barang yang cocok tidak terbuang.",
    },
    {
        "insight_order": 5,
        "topic": "Label Toko Tidak Selalu Benar (Bisa Ada Salah Ketik Bawaan)",
        "observation": "Ketika dicek satu per satu, ditemukan beberapa barang yang labelnya salah ketik dari katalog aslinya (misalnya judul barang tertulis 'Black' tetapi kolom warna tertulis 'Blue', atau baju wanita tertulis pria).",
        "retrieval_implication": "Ini bisa memicu salah paham dalam menilai kecerdasan AI. Saat pembeli mencari 'jeans biru', AI berhasil menemukan celana jeans biru yang tepat. Namun karena label database salah ketik atau belum terdaftar, sistem penilai otomatis malah menganggap AI salah.",
        "action_solution": "Sebelum sistem diuji, kita melakukan pembersihan data (data cleaning) dan sinkronisasi kunci jawaban secara cermat agar nilai performa benar-benar mencerminkan kecerdasan AI tanpa terdistorsi salah ketik label toko.",
    },
]


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    return getattr(config, "DB_PATH", config.DATA_DIR / "fashion_retrieval.db")


def get_db_connection(custom_path: Optional[Path] = None) -> sqlite3.Connection:
    path = get_db_path(custom_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


def init_db(custom_path: Optional[Path] = None):
    """Creates the SQLite database schema for all application tables."""
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()

    # 1. System Configs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_configs (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT
        );
    """)

    # 2. Target Article Types Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS target_article_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
    """)

    # 3. Retrieval Insights Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_order INTEGER NOT NULL,
            topic TEXT NOT NULL,
            observation TEXT NOT NULL,
            retrieval_implication TEXT NOT NULL,
            action_solution TEXT NOT NULL
        );
    """)

    # 4. Audit Samples Table (20 Catalog Validation Samples - Appendix A)
    cursor.execute("PRAGMA table_info(audit_samples)")
    existing_cols = [r[1] for r in cursor.fetchall()]
    if existing_cols and ("validation_status" not in existing_cols or "finding_rationale" not in existing_cols):
        cursor.execute("DROP TABLE audit_samples")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_samples (
            no INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            product_display_name TEXT,
            master_category TEXT,
            article_type TEXT,
            gender TEXT,
            base_colour TEXT,
            usage TEXT,
            image_filename TEXT,
            validation_status TEXT NOT NULL,
            finding_rationale TEXT NOT NULL
        );
    """)

    # 5. Benchmark Queries Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_queries (
            id TEXT PRIMARY KEY,
            level TEXT NOT NULL,
            query_text TEXT NOT NULL,
            target_description TEXT,
            relevance_criteria TEXT,
            total_relevant INTEGER DEFAULT 0
        );
    """)

    # 6. Benchmark Ground Truth Mapping Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_ground_truth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id TEXT NOT NULL REFERENCES benchmark_queries(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL,
            relevance_label INTEGER DEFAULT 1,
            UNIQUE(query_id, product_id)
        );
    """)

    # 7. Products Catalog Table (1,200 Evaluated / Indexed Products)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            gender TEXT,
            master_category TEXT,
            sub_category TEXT,
            article_type TEXT,
            base_colour TEXT,
            season TEXT,
            year REAL,
            usage TEXT,
            product_display_name TEXT,
            image_filename TEXT,
            is_indexed INTEGER DEFAULT 1
        );
    """)

    # 8. Benchmark Overall & By-Level Evaluation Metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_overall_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL UNIQUE,
            precision_at_5 REAL,
            precision_at_10 REAL,
            precision_at_20 REAL,
            recall_at_5 REAL,
            recall_at_10 REAL,
            recall_at_20 REAL,
            mrr REAL,
            ndcg_at_10 REAL,
            total_queries INTEGER DEFAULT 0,
            total_corpus_items INTEGER DEFAULT 1500,
            k_eval INTEGER DEFAULT 10,
            report_json TEXT
        );
    """)

    # Ensure schema migrations for benchmark_overall_metrics if table existed
    cursor.execute("PRAGMA table_info(benchmark_overall_metrics)")
    bom_cols = [r[1] for r in cursor.fetchall()]
    if bom_cols:
        if "total_corpus_items" not in bom_cols:
            cursor.execute("ALTER TABLE benchmark_overall_metrics ADD COLUMN total_corpus_items INTEGER DEFAULT 1500")
        if "k_eval" not in bom_cols:
            cursor.execute("ALTER TABLE benchmark_overall_metrics ADD COLUMN k_eval INTEGER DEFAULT 10")
        if "report_json" not in bom_cols:
            cursor.execute("ALTER TABLE benchmark_overall_metrics ADD COLUMN report_json TEXT")

    # 9. Benchmark Query Results Table (Per-Query Evaluation Metrics)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_query_results (
            query_id TEXT PRIMARY KEY REFERENCES benchmark_queries(id) ON DELETE CASCADE,
            level TEXT NOT NULL,
            query_text TEXT NOT NULL,
            ground_truth_pool INTEGER,
            precision_at_5 REAL,
            precision_at_10 REAL,
            precision_at_20 REAL,
            recall_at_5 REAL,
            recall_at_10 REAL,
            recall_at_20 REAL,
            mrr REAL,
            ndcg_at_10 REAL,
            category_acc REAL,
            color_acc REAL,
            gender_acc REAL,
            false_positives_sample TEXT
        );
    """)

    # 10. EDA Summary Report Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eda_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_file TEXT,
            total_records INTEGER,
            completeness_json TEXT,
            distribution_article_type_json TEXT,
            distribution_base_colour_top10_json TEXT,
            distribution_gender_json TEXT,
            distribution_usage_json TEXT,
            report_json TEXT
        );
    """)

    # Ensure schema migration for eda_summary if table existed
    cursor.execute("PRAGMA table_info(eda_summary)")
    eda_cols = [r[1] for r in cursor.fetchall()]
    if eda_cols and "report_json" not in eda_cols:
        cursor.execute("ALTER TABLE eda_summary ADD COLUMN report_json TEXT")

    conn.commit()
    conn.close()
    logger.info("SQLite schema initialized successfully.")


def seed_db(custom_path: Optional[Path] = None, force: bool = False):
    """Populates the SQLite database with static data currently in code & files."""
    init_db(custom_path)
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()

    # 1. Seed System Configs
    for item in DEFAULT_SYSTEM_CONFIGS:
        if force:
            cursor.execute(
                "INSERT OR REPLACE INTO system_configs (key, value, description) VALUES (?, ?, ?)",
                (item["key"], item["value"], item["description"]),
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO system_configs (key, value, description) VALUES (?, ?, ?)",
                (item["key"], item["value"], item["description"]),
            )

    # 2. Seed Target Article Types
    for idx, art_type in enumerate(DEFAULT_TARGET_ARTICLE_TYPES):
        cursor.execute(
            "INSERT OR IGNORE INTO target_article_types (name, display_order, is_active) VALUES (?, ?, 1)",
            (art_type, idx + 1),
        )

    # 3. Seed Retrieval Insights
    cursor.execute("SELECT COUNT(*) FROM retrieval_insights")
    if cursor.fetchone()[0] == 0 or force:
        if force:
            cursor.execute("DELETE FROM retrieval_insights")
        for ins in DEFAULT_RETRIEVAL_INSIGHTS:
            cursor.execute(
                """
                INSERT INTO retrieval_insights (insight_order, topic, observation, retrieval_implication, action_solution)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ins["insight_order"],
                    ins["topic"],
                    ins["observation"],
                    ins["retrieval_implication"],
                    ins["action_solution"],
                ),
            )

    # 4. Seed Audit Samples (Lampiran A)
    for sample in DEFAULT_AUDIT_SAMPLES:
        p_id = sample["product_id"]
        p_name = sample.get("product_display_name", "")
        m_cat = sample.get("master_category", "Apparel")
        a_type = sample.get("article_type", "Tshirts")
        gen = sample.get("gender", "Men")
        col = sample.get("base_colour", "Blue")
        usg = sample.get("usage", "Sports")
        img = sample.get("image_filename", f"{p_id}.jpg")

        cursor.execute(
            """
            INSERT OR REPLACE INTO audit_samples (
                no, product_id, product_display_name, master_category, article_type,
                gender, base_colour, usage, image_filename, validation_status, finding_rationale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sample["no"],
                p_id,
                p_name,
                m_cat,
                a_type,
                gen,
                col,
                usg,
                img,
                sample.get("validation_status", "Konsisten"),
                sample.get("finding_rationale", ""),
            ),
        )

        # Also ensure product is present in products table
        cursor.execute(
            """
            INSERT OR IGNORE INTO products (
                id, gender, master_category, sub_category, article_type, base_colour,
                season, year, usage, product_display_name, image_filename, is_indexed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                p_id,
                gen,
                m_cat,
                "Topwear",
                a_type,
                col,
                "Summer",
                2012.0,
                usg,
                p_name,
                img,
                0,
            ),
        )

    # 5. Seed Products from metadata cache or clean styles
    cursor.execute("SELECT COUNT(*) FROM products")
    prod_count = cursor.fetchone()[0]
    if prod_count == 0 or force:
        products_source_path = config.METADATA_CACHE_PATH
        if products_source_path.exists():
            df_prods = pd.read_parquet(products_source_path)
            logger.info(f"Seeding {len(df_prods)} products into SQLite from {products_source_path}")
            records = []
            for _, r in df_prods.iterrows():
                records.append((
                    int(r["id"]),
                    str(r.get("gender", "")),
                    str(r.get("masterCategory", "")),
                    str(r.get("subCategory", "")),
                    str(r.get("articleType", "")),
                    str(r.get("baseColour", "")),
                    str(r.get("season", "")),
                    float(r["year"]) if pd.notna(r.get("year")) else None,
                    str(r.get("usage", "")),
                    str(r.get("productDisplayName", "")),
                    str(r.get("image_filename", f"{r['id']}.jpg")),
                    1,
                ))
            cursor.executemany(
                """
                INSERT OR REPLACE INTO products (
                    id, gender, master_category, sub_category, article_type, base_colour,
                    season, year, usage, product_display_name, image_filename, is_indexed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )

    conn.commit()
    conn.close()

    # 6. Seed Benchmark Queries and Ground Truth
    gt_json_path = config.GROUND_TRUTH_JSON_PATH
    if gt_json_path.exists():
        try:
            with open(gt_json_path, "r", encoding="utf-8") as f:
                gt_data = json.load(f)
            save_benchmark_ground_truth_to_db(gt_data, custom_path=custom_path)
        except Exception as e:
            logger.warning(f"Could not seed benchmark ground truth from JSON: {e}")

    # 7. Seed Benchmark Results if existing
    bench_results_json = config.PROCESSED_DATA_DIR / "benchmark_results.json"
    if bench_results_json.exists():
        try:
            with open(bench_results_json, "r", encoding="utf-8") as f:
                res_data = json.load(f)
            save_benchmark_report_to_db(res_data, custom_path=custom_path)
        except Exception as e:
            logger.warning(f"Could not seed benchmark results from JSON: {e}")

    # 8. Seed EDA Summary if existing
    eda_json = config.PROCESSED_DATA_DIR / "eda_report.json"
    if eda_json.exists():
        try:
            with open(eda_json, "r", encoding="utf-8") as f:
                eda_data = json.load(f)
            save_eda_report_to_db(eda_data, custom_path=custom_path)
        except Exception as e:
            logger.warning(f"Could not seed EDA summary from JSON: {e}")

    logger.info("SQLite database successfully seeded with static data.")


# Repository / Query Functions

def get_system_configs() -> Dict[str, str]:
    """Returns key-value dictionary of all system configurations from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM system_configs")
    rows = cursor.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def get_target_article_types() -> List[str]:
    """Returns active target article types from SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM target_article_types WHERE is_active = 1 ORDER BY display_order ASC")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [r["name"] for r in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch target article types from DB: {e}")
    return DEFAULT_TARGET_ARTICLE_TYPES


def get_retrieval_insights() -> List[Dict[str, Any]]:
    """Returns 5 Key Multimodal Retrieval Insights from SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT topic, observation, retrieval_implication, action_solution FROM retrieval_insights ORDER BY insight_order ASC"
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch retrieval insights from DB: {e}")
    return DEFAULT_RETRIEVAL_INSIGHTS


def get_audit_samples() -> List[Dict[str, Any]]:
    """Returns the 20 catalog validation audit samples (Appendix A) from SQLite."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT no, product_id as id, product_display_name as productDisplayName,
                   master_category as masterCategory, article_type as articleType,
                   gender, base_colour as baseColour, usage, image_filename,
                   validation_status, finding_rationale
            FROM audit_samples ORDER BY no ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch audit samples from DB: {e}")
    return [
        {
            "no": s["no"],
            "id": s["product_id"],
            "productDisplayName": s["product_display_name"],
            "masterCategory": s["master_category"],
            "articleType": s["article_type"],
            "gender": s["gender"],
            "baseColour": s["base_colour"],
            "usage": s["usage"],
            "image_filename": s["image_filename"],
            "validation_status": s.get("validation_status", "Konsisten"),
            "finding_rationale": s.get("finding_rationale", ""),
        }
        for s in DEFAULT_AUDIT_SAMPLES
    ]


def save_benchmark_ground_truth_to_db(gt_data: Dict[str, Any], custom_path: Optional[Path] = None):
    """Persists benchmark queries and ground truth mappings into SQLite database."""
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()
    for q_id, q_info in gt_data.items():
        total_rel = q_info.get("total_relevant_answers", len(q_info.get("relevant_product_ids", [])))
        cursor.execute(
            """
            INSERT OR REPLACE INTO benchmark_queries (id, level, query_text, target_description, relevance_criteria, total_relevant)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                q_id,
                q_info.get("specificity", q_info.get("level", "General")),
                q_info.get("query_text", q_info.get("text", "")),
                q_info.get("target_description", ""),
                q_info.get("relevance_criteria", ""),
                total_rel,
            ),
        )
        rel_ids = q_info.get("relevant_product_ids", [])
        cursor.execute("DELETE FROM benchmark_ground_truth WHERE query_id = ?", (q_id,))
        for p_id in rel_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO benchmark_ground_truth (query_id, product_id, relevance_label) VALUES (?, ?, 1)",
                (q_id, int(p_id)),
            )
    conn.commit()
    conn.close()
    logger.info("Saved benchmark ground truth to SQLite database.")


def get_benchmark_ground_truth_dict(custom_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Returns the benchmark ground truth in the exact dictionary format of benchmark_ground_truth.json directly from SQLite."""
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, level, query_text, target_description, relevance_criteria, total_relevant FROM benchmark_queries ORDER BY id ASC")
    queries = cursor.fetchall()
    result = {}
    for q in queries:
        cursor.execute("SELECT product_id FROM benchmark_ground_truth WHERE query_id = ? ORDER BY product_id ASC", (q["id"],))
        p_ids = [int(r["product_id"]) for r in cursor.fetchall()]
        result[q["id"]] = {
            "query_text": q["query_text"],
            "specificity": q["level"],
            "target_description": q["target_description"] or "",
            "relevance_criteria": q["relevance_criteria"] or "",
            "total_relevant_answers": q["total_relevant"] if q["total_relevant"] is not None else len(p_ids),
            "relevant_product_ids": p_ids,
        }
    conn.close()
    return result


def get_ground_truth_product_ids(custom_path: Optional[Path] = None) -> Set[int]:
    """Returns set of all unique product IDs belonging to the benchmark ground truth from SQLite."""
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT product_id FROM benchmark_ground_truth")
    ids = {int(r["product_id"]) for r in cursor.fetchall()}
    conn.close()
    return ids


def get_benchmark_queries(with_relevant_ids: bool = True, custom_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns all 30 benchmark queries with associated ground truth candidate IDs from SQLite."""
    try:
        conn = get_db_connection(custom_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, level, query_text as text, target_description, relevance_criteria, total_relevant FROM benchmark_queries ORDER BY id ASC")
        query_rows = cursor.fetchall()

        queries = []
        for q in query_rows:
            q_dict = dict(q)
            if with_relevant_ids:
                cursor.execute("SELECT product_id FROM benchmark_ground_truth WHERE query_id = ?", (q_dict["id"],))
                p_rows = cursor.fetchall()
                rel_ids = {int(r["product_id"]) for r in p_rows}
                q_dict["relevant_ids"] = rel_ids
                if not q_dict.get("total_relevant"):
                    q_dict["total_relevant"] = len(rel_ids)
            queries.append(q_dict)

        conn.close()
        if queries:
            return queries
    except Exception as e:
        logger.warning(f"Failed to fetch benchmark queries from DB: {e}")
    return []


def get_benchmark_report_from_db(custom_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetches benchmark evaluation results and metrics from SQLite."""
    try:
        conn = get_db_connection(custom_path)
        cursor = conn.cursor()

        # Overall metrics
        cursor.execute("SELECT * FROM benchmark_overall_metrics WHERE scope = 'overall'")
        om_row = cursor.fetchone()
        if not om_row:
            conn.close()
            return None

        overall_metrics = {
            "precision@5": round(om_row["precision_at_5"], 4) if om_row["precision_at_5"] is not None else 0.0,
            "precision@10": round(om_row["precision_at_10"], 4) if om_row["precision_at_10"] is not None else 0.0,
            "precision@20": round(om_row["precision_at_20"], 4) if om_row["precision_at_20"] is not None else 0.0,
            "recall@5": round(om_row["recall_at_5"], 4) if om_row["recall_at_5"] is not None else 0.0,
            "recall@10": round(om_row["recall_at_10"], 4) if om_row["recall_at_10"] is not None else 0.0,
            "recall@20": round(om_row["recall_at_20"], 4) if om_row["recall_at_20"] is not None else 0.0,
        }

        # By level metrics - standardize to General, Medium, Specific
        cursor.execute("SELECT * FROM benchmark_overall_metrics WHERE scope IN ('General', 'Medium', 'Specific') ORDER BY id ASC")
        lvl_rows = cursor.fetchall()
        metrics_by_level = {}
        for r in lvl_rows:
            metrics_by_level[r["scope"]] = {
                "precision@5": round(r["precision_at_5"], 4) if r["precision_at_5"] is not None else 0.0,
                "precision@10": round(r["precision_at_10"], 4) if r["precision_at_10"] is not None else 0.0,
                "precision@20": round(r["precision_at_20"], 4) if r["precision_at_20"] is not None else 0.0,
                "recall@5": round(r["recall_at_5"], 4) if r["recall_at_5"] is not None else 0.0,
                "recall@10": round(r["recall_at_10"], 4) if r["recall_at_10"] is not None else 0.0,
                "recall@20": round(r["recall_at_20"], 4) if r["recall_at_20"] is not None else 0.0,
            }

        # Query details
        cursor.execute("SELECT * FROM benchmark_query_results ORDER BY query_id ASC")
        q_rows = cursor.fetchall()
        query_details = []
        for r in q_rows:
            q_item = {
                "id": r["query_id"],
                "level": r["level"],
                "query": r["query_text"],
                "ground_truth_pool": r["ground_truth_pool"],
                "precision@5": r["precision_at_5"],
                "precision@10": r["precision_at_10"],
                "precision@20": r["precision_at_20"],
                "recall@5": r["recall_at_5"],
                "recall@10": r["recall_at_10"],
                "recall@20": r["recall_at_20"],
                "false_positives_sample": json.loads(r["false_positives_sample"]) if r["false_positives_sample"] else [],
            }
            if "mrr" in r.keys() and r["mrr"] is not None:
                q_item["mrr"] = r["mrr"]
            if "ndcg_at_10" in r.keys() and r["ndcg_at_10"] is not None:
                q_item["ndcg@10"] = r["ndcg_at_10"]
            if "category_acc" in r.keys() and r["category_acc"] is not None:
                q_item["category_acc"] = r["category_acc"]
            if "color_acc" in r.keys() and r["color_acc"] is not None:
                q_item["color_acc"] = r["color_acc"]
            query_details.append(q_item)

        if not query_details and om_row.get("report_json"):
            try:
                rep_data = json.loads(om_row["report_json"])
                query_details = rep_data.get("query_details", [])
            except Exception:
                pass

        total_corpus = 1500
        if "total_corpus_items" in om_row.keys() and om_row["total_corpus_items"]:
            total_corpus = om_row["total_corpus_items"]

        k_val = 10
        if "k_eval" in om_row.keys() and om_row["k_eval"]:
            k_val = om_row["k_eval"]

        conn.close()
        return {
            "total_queries": om_row["total_queries"] or len(query_details),
            "total_corpus_items": total_corpus,
            "k_eval": k_val,
            "overall_metrics": overall_metrics,
            "metrics_by_level": metrics_by_level,
            "query_details": query_details,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch benchmark report from DB: {e}")
        return None


def save_benchmark_report_to_db(report: Dict[str, Any], custom_path: Optional[Path] = None):
    """Saves benchmark execution results to SQLite."""
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()

    total_queries = report.get("total_queries", 30)
    total_corpus_items = report.get("total_corpus_items", 1500)
    k_eval = report.get("k_eval", 10)
    report_json_str = json.dumps(report)

    # Clean old non-standard scopes to avoid duplicates
    cursor.execute("DELETE FROM benchmark_overall_metrics WHERE scope IN ('Umum', 'Menengah', 'Spesifik')")

    om = report.get("overall_metrics", {})
    if om:
        cursor.execute(
            """
            INSERT OR REPLACE INTO benchmark_overall_metrics (
                scope, precision_at_5, precision_at_10, precision_at_20,
                recall_at_5, recall_at_10, recall_at_20, total_queries,
                total_corpus_items, k_eval, report_json
            ) VALUES ('overall', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                om.get("precision@5"),
                om.get("precision@10"),
                om.get("precision@20"),
                om.get("recall@5"),
                om.get("recall@10"),
                om.get("recall@20"),
                total_queries,
                total_corpus_items,
                k_eval,
                report_json_str,
            ),
        )

    for lvl, lm in report.get("metrics_by_level", {}).items():
        cursor.execute(
            """
            INSERT OR REPLACE INTO benchmark_overall_metrics (
                scope, precision_at_5, precision_at_10, precision_at_20,
                recall_at_5, recall_at_10, recall_at_20, total_queries,
                total_corpus_items, k_eval
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lvl,
                lm.get("precision@5"),
                lm.get("precision@10"),
                lm.get("precision@20"),
                lm.get("recall@5"),
                lm.get("recall@10"),
                lm.get("recall@20"),
                10,
                total_corpus_items,
                k_eval,
            ),
        )

    for q in report.get("query_details", []):
        cursor.execute(
            """
            INSERT OR REPLACE INTO benchmark_query_results (
                query_id, level, query_text, ground_truth_pool,
                precision_at_5, precision_at_10, precision_at_20,
                recall_at_5, recall_at_10, recall_at_20,
                mrr, ndcg_at_10, category_acc, color_acc, gender_acc, false_positives_sample
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                q.get("id"),
                q.get("level"),
                q.get("query"),
                q.get("ground_truth_pool"),
                q.get("precision@5"),
                q.get("precision@10"),
                q.get("precision@20"),
                q.get("recall@5"),
                q.get("recall@10"),
                q.get("recall@20"),
                q.get("mrr"),
                q.get("ndcg@10"),
                q.get("category_acc"),
                q.get("color_acc"),
                q.get("gender_acc"),
                json.dumps(q.get("false_positives_sample", [])),
            ),
        )

    conn.commit()
    conn.close()
    logger.info("Saved benchmark evaluation results to SQLite database.")


def get_eda_report_from_db(custom_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetches EDA report statistics and verification samples from SQLite."""
    try:
        conn = get_db_connection(custom_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM eda_summary ORDER BY id DESC LIMIT 1")
        summary_row = cursor.fetchone()
        if not summary_row:
            conn.close()
            return None

        # Fetch audit samples directly from audit_samples table
        cursor.execute(
            """
            SELECT no, product_id as id, product_display_name as productDisplayName,
                   master_category as masterCategory, article_type as articleType,
                   gender, base_colour as baseColour, usage, image_filename,
                   validation_status, finding_rationale
            FROM audit_samples ORDER BY no ASC
            """
        )
        audit_rows = [dict(r) for r in cursor.fetchall()]

        # Enrich audit samples with product info if anything was empty
        enriched_samples = []
        for sample in audit_rows:
            s_dict = dict(sample)
            if not s_dict.get("productDisplayName"):
                cursor.execute(
                    """
                    SELECT product_display_name, master_category, article_type, gender, base_colour, usage, image_filename
                    FROM products WHERE id = ?
                    """,
                    (sample["id"],),
                )
                prod_row = cursor.fetchone()
                if prod_row:
                    s_dict["productDisplayName"] = prod_row["product_display_name"]
                    s_dict["masterCategory"] = prod_row["master_category"]
                    s_dict["articleType"] = prod_row["article_type"]
                    s_dict["gender"] = prod_row["gender"]
                    s_dict["baseColour"] = prod_row["base_colour"]
                    s_dict["usage"] = prod_row["usage"]
                    s_dict["image_filename"] = prod_row["image_filename"]

            # Check if image exists
            img_file = s_dict["image_filename"]
            img_path = config.IMAGES_DIR / img_file
            s_dict["image_exists"] = img_path.exists()
            s_dict["resolution"] = "60x80" if img_path.exists() else "Unknown"
            enriched_samples.append(s_dict)

        # Fetch insights
        cursor.execute("SELECT topic, observation, retrieval_implication, action_solution FROM retrieval_insights ORDER BY insight_order ASC")
        insights = [dict(r) for r in cursor.fetchall()]

        # Extract multivariate_analysis from report_json if present
        full_report_obj = {}
        if summary_row["report_json"]:
            try:
                full_report_obj = json.loads(summary_row["report_json"])
            except Exception:
                pass

        multivariate_data = full_report_obj.get("multivariate_analysis")

        conn.close()
        return {
            "dataset_file": summary_row["dataset_file"],
            "total_records": summary_row["total_records"],
            "metadata_completeness": json.loads(summary_row["completeness_json"]),
            "distribution_articleType": json.loads(summary_row["distribution_article_type_json"]),
            "distribution_baseColour_top10": json.loads(summary_row["distribution_base_colour_top10_json"]),
            "distribution_gender": json.loads(summary_row["distribution_gender_json"]),
            "distribution_usage": json.loads(summary_row["distribution_usage_json"]),
            "visual_verification_20_pairs": enriched_samples,
            "insights": insights,
            "multivariate_analysis": multivariate_data,
        }
    except Exception as e:
        logger.warning(f"Failed to fetch EDA report from DB: {e}")
        return None


def get_multivariate_report_from_db(custom_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetches multivariate and co-occurrence analysis from SQLite database, computing on the fly if needed."""
    try:
        report = get_eda_report_from_db(custom_path)
        if report and report.get("multivariate_analysis"):
            return report["multivariate_analysis"]
        
        # If not found in DB, run calculation dynamically
        from src.data.multivariate import MultivariateAnalyzer
        analyzer = MultivariateAnalyzer()
        multi_data = analyzer.run_full_analysis()
        return multi_data
    except Exception as e:
        logger.warning(f"Failed to fetch multivariate report: {e}")
        return None



def save_eda_report_to_db(report: Dict[str, Any], custom_path: Optional[Path] = None):
    """Saves EDA analysis report into SQLite."""
    conn = get_db_connection(custom_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM eda_summary")
    cursor.execute(
        """
        INSERT INTO eda_summary (
            dataset_file, total_records, completeness_json,
            distribution_article_type_json, distribution_base_colour_top10_json,
            distribution_gender_json, distribution_usage_json, report_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report.get("dataset_file", "subset_1500_eval.csv"),
            report.get("total_records", 1500),
            json.dumps(report.get("metadata_completeness", {})),
            json.dumps(report.get("distribution_articleType", {})),
            json.dumps(report.get("distribution_baseColour_top10", {})),
            json.dumps(report.get("distribution_gender", {})),
            json.dumps(report.get("distribution_usage", {})),
            json.dumps(report),
        ),
    )

    # Update visual verification audit samples if provided
    samples = report.get("visual_verification_20_pairs", [])
    if samples:
        for idx, sample in enumerate(samples):
            p_id = sample.get("id") or sample.get("product_id")
            cursor.execute(
                """
                INSERT OR REPLACE INTO audit_samples (
                    no, product_id, product_display_name, master_category, article_type,
                    gender, base_colour, usage, image_filename, validation_status, finding_rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sample.get("no", idx + 1),
                    p_id,
                    sample.get("productDisplayName", sample.get("product_display_name", "")),
                    sample.get("masterCategory", sample.get("master_category", "")),
                    sample.get("articleType", sample.get("article_type", "")),
                    sample.get("gender", ""),
                    sample.get("baseColour", sample.get("base_colour", "")),
                    sample.get("usage", ""),
                    sample.get("image_filename", f"{p_id}.jpg"),
                    sample.get("validation_status", "Konsisten"),
                    sample.get("finding_rationale", ""),
                ),
            )

    # Also update/insert retrieval insights if present
    if "insights" in report and report["insights"]:
        cursor.execute("DELETE FROM retrieval_insights")
        for idx, ins in enumerate(report["insights"]):
            cursor.execute(
                """
                INSERT INTO retrieval_insights (insight_order, topic, observation, retrieval_implication, action_solution)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    idx + 1,
                    ins["topic"],
                    ins["observation"],
                    ins["retrieval_implication"],
                    ins.get("action_solution", ""),
                ),
            )

    conn.commit()
    conn.close()
    logger.info("Saved EDA report to SQLite database.")


def get_products_dict() -> Dict[int, Dict[str, Any]]:
    """Returns dictionary mapping product_id to product metadata dictionary from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, gender, master_category as masterCategory, sub_category as subCategory,
               article_type as articleType, base_colour as baseColour, season, year,
               usage, product_display_name as productDisplayName, image_filename
        FROM products
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return {int(r["id"]): dict(r) for r in rows}


def get_ground_truth_relations(
    query_id: Optional[str] = None,
    level: Optional[str] = None,
    article_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Returns joined benchmark ground truth relations with product metadata and query details."""
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = """
        SELECT 
            bgt.id,
            bgt.query_id,
            bq.query_text,
            bq.level as query_level,
            bq.target_description,
            bq.relevance_criteria,
            bgt.product_id,
            p.product_display_name as product_name,
            p.master_category,
            p.sub_category,
            p.article_type,
            p.base_colour,
            p.gender,
            p.usage,
            p.image_filename,
            bgt.relevance_label
        FROM benchmark_ground_truth bgt
        JOIN benchmark_queries bq ON bgt.query_id = bq.id
        LEFT JOIN products p ON bgt.product_id = p.id
        WHERE 1=1
    """
    params = []
    if query_id:
        sql += " AND bgt.query_id = ?"
        params.append(query_id)
    if level:
        sql += " AND bq.level = ?"
        params.append(level)
    if article_type:
        sql += " AND p.article_type = ?"
        params.append(article_type)
    if search:
        sql += " AND (p.product_display_name LIKE ? OR bq.query_text LIKE ? OR CAST(bgt.product_id AS TEXT) LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])

    sql += " ORDER BY bgt.query_id ASC, bgt.product_id ASC"

    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

    cursor.execute(sql, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_ground_truth_summary() -> Dict[str, Any]:
    """Returns aggregated summary of ground truth relations, unique products, and queries."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM benchmark_ground_truth")
    total_pairs = cursor.fetchone()[0]

    cursor.execute("SELECT count(DISTINCT product_id) FROM benchmark_ground_truth")
    unique_products = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM benchmark_queries")
    total_queries = cursor.fetchone()[0]

    cursor.execute("""
        SELECT bq.level, count(bgt.id) as pair_count, count(DISTINCT bgt.product_id) as prod_count, count(DISTINCT bq.id) as query_count
        FROM benchmark_ground_truth bgt
        JOIN benchmark_queries bq ON bgt.query_id = bq.id
        GROUP BY bq.level
    """)
    level_breakdown = {r["level"]: dict(r) for r in cursor.fetchall()}

    cursor.execute("""
        SELECT p.article_type, count(bgt.id) as pair_count
        FROM benchmark_ground_truth bgt
        LEFT JOIN products p ON bgt.product_id = p.id
        GROUP BY p.article_type
        ORDER BY pair_count DESC
    """)
    category_breakdown = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT id, query_text, level, target_description, relevance_criteria, total_relevant
        FROM benchmark_queries
        ORDER BY id ASC
    """)
    queries = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total_pairs": total_pairs,
        "unique_products": unique_products,
        "total_queries": total_queries,
        "level_breakdown": level_breakdown,
        "category_breakdown": category_breakdown,
        "queries": queries,
    }


if __name__ == "__main__":
    logger.info("Initializing and seeding SQLite database")
    seed_db(force=True)
    logger.info("Database setup complete.")

