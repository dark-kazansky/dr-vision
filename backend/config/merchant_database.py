"""
Merchant Database — Vietnamese merchant mapping for transaction categorization.

Maps merchant names commonly found in Vietnamese bank statements to categories
and subcategories. Used by TransactionCategorizer for rule-based matching.

Usage:
    from config.merchant_database import MERCHANT_DB, lookup_merchant
"""

from __future__ import annotations

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class MerchantInfo:
    """Merchant category mapping."""
    category: str
    subcategory: str = ""


# =============================================================================
# MERCHANT DATABASE
# =============================================================================

MERCHANT_DB: Dict[str, MerchantInfo] = {
    # ─── Food & Dining: Cafe ───
    "THE COFFEE HOUSE": MerchantInfo("food_dining", "cafe"),
    "HIGHLANDS COFFEE": MerchantInfo("food_dining", "cafe"),
    "HIGHLANDS": MerchantInfo("food_dining", "cafe"),
    "STARBUCKS": MerchantInfo("food_dining", "cafe"),
    "PHUC LONG": MerchantInfo("food_dining", "cafe"),
    "TRUNG NGUYEN": MerchantInfo("food_dining", "cafe"),
    "CONG CA PHE": MerchantInfo("food_dining", "cafe"),

    # ─── Food & Dining: Fast food ───
    "JOLLIBEE": MerchantInfo("food_dining", "fast_food"),
    "LOTTERIA": MerchantInfo("food_dining", "fast_food"),
    "KFC": MerchantInfo("food_dining", "fast_food"),
    "MCDONALDS": MerchantInfo("food_dining", "fast_food"),
    "BURGER KING": MerchantInfo("food_dining", "fast_food"),
    "PIZZA HUT": MerchantInfo("food_dining", "fast_food"),
    "DOMINOS": MerchantInfo("food_dining", "fast_food"),

    # ─── Food & Dining: Delivery ───
    "GRAB FOOD": MerchantInfo("food_dining", "delivery"),
    "GRABFOOD": MerchantInfo("food_dining", "delivery"),
    "SHOPEE FOOD": MerchantInfo("food_dining", "delivery"),
    "SHOPEEFOOD": MerchantInfo("food_dining", "delivery"),
    "BAEMIN": MerchantInfo("food_dining", "delivery"),
    "NOW": MerchantInfo("food_dining", "delivery"),
    "LOSHIP": MerchantInfo("food_dining", "delivery"),

    # ─── Food & Dining: Restaurant ───
    "GOLDEN GATE": MerchantInfo("food_dining", "restaurant"),
    "REDSUN": MerchantInfo("food_dining", "restaurant"),
    "SUMO BBQ": MerchantInfo("food_dining", "restaurant"),
    "KICHI KICHI": MerchantInfo("food_dining", "restaurant"),
    "GOGI HOUSE": MerchantInfo("food_dining", "restaurant"),

    # ─── Shopping: E-commerce ───
    "SHOPEE": MerchantInfo("shopping", "ecommerce"),
    "LAZADA": MerchantInfo("shopping", "ecommerce"),
    "TIKI": MerchantInfo("shopping", "ecommerce"),
    "SENDO": MerchantInfo("shopping", "ecommerce"),
    "AMAZON": MerchantInfo("shopping", "ecommerce"),
    "TIKTOK SHOP": MerchantInfo("shopping", "ecommerce"),

    # ─── Shopping: Mall ───
    "VINCOM": MerchantInfo("shopping", "mall"),
    "AEON MALL": MerchantInfo("shopping", "mall"),
    "AEON": MerchantInfo("shopping", "mall"),
    "LOTTE MALL": MerchantInfo("shopping", "mall"),
    "TAKASHIMAYA": MerchantInfo("shopping", "mall"),
    "SAIGON CENTRE": MerchantInfo("shopping", "mall"),

    # ─── Shopping: Electronics ───
    "THE GIOI DI DONG": MerchantInfo("shopping", "electronics"),
    "THEGIOIDIDONG": MerchantInfo("shopping", "electronics"),
    "DIEN MAY XANH": MerchantInfo("shopping", "electronics"),
    "FPT SHOP": MerchantInfo("shopping", "electronics"),
    "CELLPHONES": MerchantInfo("shopping", "electronics"),
    "NGUYEN KIM": MerchantInfo("shopping", "electronics"),

    # ─── Shopping: Fashion ───
    "CANIFA": MerchantInfo("shopping", "fashion"),
    "UNIQLO": MerchantInfo("shopping", "fashion"),
    "ZARA": MerchantInfo("shopping", "fashion"),
    "H&M": MerchantInfo("shopping", "fashion"),

    # ─── Groceries ───
    "VINMART": MerchantInfo("groceries", "supermarket"),
    "WIN MART": MerchantInfo("groceries", "supermarket"),
    "WINMART": MerchantInfo("groceries", "supermarket"),
    "BACH HOA XANH": MerchantInfo("groceries", "convenience"),
    "CO.OP MART": MerchantInfo("groceries", "supermarket"),
    "COOPMART": MerchantInfo("groceries", "supermarket"),
    "BIG C": MerchantInfo("groceries", "hypermarket"),
    "GO!": MerchantInfo("groceries", "hypermarket"),
    "LOTTE MART": MerchantInfo("groceries", "hypermarket"),
    "MEGA MARKET": MerchantInfo("groceries", "hypermarket"),
    "EMART": MerchantInfo("groceries", "hypermarket"),
    "MINISTOP": MerchantInfo("groceries", "convenience"),
    "CIRCLE K": MerchantInfo("groceries", "convenience"),
    "GS25": MerchantInfo("groceries", "convenience"),
    "7-ELEVEN": MerchantInfo("groceries", "convenience"),
    "FAMILY MART": MerchantInfo("groceries", "convenience"),

    # ─── Transportation: Ride hailing ───
    "GRAB": MerchantInfo("transportation", "ride_hailing"),
    "BE": MerchantInfo("transportation", "ride_hailing"),
    "BE GROUP": MerchantInfo("transportation", "ride_hailing"),
    "GOJEK": MerchantInfo("transportation", "ride_hailing"),

    # ─── Transportation: Fuel ───
    "PETROLIMEX": MerchantInfo("transportation", "fuel"),
    "PVOIL": MerchantInfo("transportation", "fuel"),
    "SAIGON PETRO": MerchantInfo("transportation", "fuel"),

    # ─── Transportation: Airlines ───
    "VIETNAM AIRLINES": MerchantInfo("transportation", "airline"),
    "VIETJET": MerchantInfo("transportation", "airline"),
    "VIETJET AIR": MerchantInfo("transportation", "airline"),
    "BAMBOO AIRWAYS": MerchantInfo("transportation", "airline"),

    # ─── Transportation: Parking / Toll ───
    "VETC": MerchantInfo("transportation", "toll"),
    "EPASS": MerchantInfo("transportation", "toll"),

    # ─── Utilities: Electricity ───
    "EVN": MerchantInfo("utilities", "electricity"),
    "EVNHCMC": MerchantInfo("utilities", "electricity"),
    "TIEN DIEN": MerchantInfo("utilities", "electricity"),

    # ─── Utilities: Telecom ───
    "VNPT": MerchantInfo("utilities", "telecom"),
    "VIETTEL": MerchantInfo("utilities", "telecom"),
    "MOBIFONE": MerchantInfo("utilities", "telecom"),
    "VIETNAMOBILE": MerchantInfo("utilities", "telecom"),

    # ─── Utilities: Internet ───
    "FPT TELECOM": MerchantInfo("utilities", "internet"),
    "FPT": MerchantInfo("utilities", "internet"),
    "SCTV": MerchantInfo("utilities", "internet"),
    "CMC TELECOM": MerchantInfo("utilities", "internet"),

    # ─── Utilities: Water ───
    "NUOC": MerchantInfo("utilities", "water"),
    "SAWACO": MerchantInfo("utilities", "water"),

    # ─── Entertainment: Streaming ───
    "NETFLIX": MerchantInfo("entertainment", "streaming"),
    "SPOTIFY": MerchantInfo("entertainment", "streaming"),
    "YOUTUBE": MerchantInfo("entertainment", "streaming"),
    "APPLE": MerchantInfo("entertainment", "digital"),
    "GOOGLE PLAY": MerchantInfo("entertainment", "digital"),
    "STEAM": MerchantInfo("entertainment", "gaming"),

    # ─── Entertainment: Cinema ───
    "CGV": MerchantInfo("entertainment", "cinema"),
    "GALAXY": MerchantInfo("entertainment", "cinema"),
    "LOTTE CINEMA": MerchantInfo("entertainment", "cinema"),
    "BHD STAR": MerchantInfo("entertainment", "cinema"),

    # ─── Healthcare ───
    "MEDICARE": MerchantInfo("healthcare", "hospital"),
    "VINMEC": MerchantInfo("healthcare", "hospital"),
    "NHA THUOC": MerchantInfo("healthcare", "pharmacy"),
    "PHARMACITY": MerchantInfo("healthcare", "pharmacy"),
    "LONG CHAU": MerchantInfo("healthcare", "pharmacy"),
    "AN KHANG": MerchantInfo("healthcare", "pharmacy"),
    "GUARDIAN": MerchantInfo("healthcare", "pharmacy"),

    # ─── Education ───
    "UDEMY": MerchantInfo("education", "online_course"),
    "COURSERA": MerchantInfo("education", "online_course"),
    "HOC PHI": MerchantInfo("education", "tuition"),
    "YOLA": MerchantInfo("education", "language"),
    "VUS": MerchantInfo("education", "language"),
    "ILA": MerchantInfo("education", "language"),

    # ─── Insurance ───
    "PRUDENTIAL": MerchantInfo("insurance", "life"),
    "MANULIFE": MerchantInfo("insurance", "life"),
    "AIA": MerchantInfo("insurance", "life"),
    "DAI-ICHI": MerchantInfo("insurance", "life"),
    "BAO VIET": MerchantInfo("insurance", "general"),
    "PVI": MerchantInfo("insurance", "general"),
    "BIC": MerchantInfo("insurance", "general"),

    # ─── Investment ───
    "VNDS": MerchantInfo("investment", "securities"),
    "SSI": MerchantInfo("investment", "securities"),
    "VNDIRECT": MerchantInfo("investment", "securities"),
    "TCBS": MerchantInfo("investment", "securities"),
    "FINHAY": MerchantInfo("investment", "fund"),
}


# =============================================================================
# CATEGORY RULES (keyword + pattern matching)
# =============================================================================

CATEGORY_RULES: Dict[str, Dict] = {
    "salary": {
        "keywords": ["luong", "salary", "bonus", "thuong", "phu cap", "tien luong"],
        "patterns": [r"LUONG\s+T\d{1,2}", r"SALARY\s+\d{4}", r"LUONG\s+THANG"],
        "direction": "credit",
    },
    "transfer_in": {
        "keywords": [],
        "patterns": [r"CT\s+TU\s+", r"NHAN\s+TIEN", r"CHUYEN\s+DEN"],
        "direction": "credit",
    },
    "transfer_out": {
        "keywords": [],
        "patterns": [r"CK\s+CHO\s+", r"CHUYEN\s+KHOAN\s+CHO", r"CK\s+DEN\s+"],
        "direction": "debit",
    },
    "food_dining": {
        "keywords": ["grab food", "shopee food", "baemin", "coffee", "ca phe", "an uong", "nha hang", "quan an"],
        "patterns": [],
        "direction": "debit",
    },
    "groceries": {
        "keywords": ["vinmart", "bach hoa", "sieu thi", "co.op", "big c", "lotte mart"],
        "patterns": [],
        "direction": "debit",
    },
    "transportation": {
        "keywords": ["grab", "be", "gojek", "xang", "petrol", "ve may bay", "taxi"],
        "patterns": [r"VETC", r"EPASS"],
        "direction": "debit",
    },
    "utilities": {
        "keywords": ["evn", "vnpt", "viettel", "fpt", "nuoc", "dien", "internet", "cuoc"],
        "patterns": [r"TIEN\s+DIEN", r"CUOC\s+DIEN\s+THOAI", r"CUOC\s+INTERNET"],
        "direction": "debit",
    },
    "rent_mortgage": {
        "keywords": ["thue nha", "tien nha", "tra gop nha"],
        "patterns": [r"TIEN\s+THUE\s+NHA", r"TIEN\s+NHA\s+T\d{1,2}"],
        "direction": "debit",
    },
    "healthcare": {
        "keywords": ["benh vien", "bv", "nha thuoc", "kham", "pharmacy", "thuoc"],
        "patterns": [r"BV\s+", r"PKD\s+"],
        "direction": "debit",
    },
    "education": {
        "keywords": ["hoc phi", "truong", "school", "university", "dai hoc", "khoa hoc"],
        "patterns": [r"HOC\s+PHI"],
        "direction": "debit",
    },
    "entertainment": {
        "keywords": ["netflix", "spotify", "game", "cgv", "cinema", "phim"],
        "patterns": [],
        "direction": "debit",
    },
    "shopping": {
        "keywords": ["shopee", "lazada", "tiki", "sendo", "amazon", "mua sam"],
        "patterns": [],
        "direction": "debit",
    },
    "insurance": {
        "keywords": ["bao hiem", "prudential", "manulife", "aia", "bhxh"],
        "patterns": [r"PHI\s+BH", r"BAO\s+HIEM"],
        "direction": "debit",
    },
    "investment": {
        "keywords": ["chung khoan", "tiet kiem", "dau tu", "vnds", "ssi"],
        "patterns": [r"TIET\s+KIEM", r"GUI\s+TK"],
        "direction": "debit",
    },
    "loan_payment": {
        "keywords": ["tra gop", "tra lai", "tra no", "khoan vay"],
        "patterns": [r"TRA\s+GOP", r"TRA\s+LAI\s+VAY", r"TRA\s+NO"],
        "direction": "debit",
    },
    "fee_charge": {
        "keywords": ["phi", "fee", "charge", "thuong nien"],
        "patterns": [r"PHI\s+(SMS|DV|THE|CK|QTHT|TK)", r"PHI\s+DICH\s+VU"],
        "direction": "debit",
    },
    "interest_earned": {
        "keywords": ["lai", "interest", "tiet kiem"],
        "patterns": [r"LAI\s+(TK|TG|TIET\s+KIEM)", r"LAI\s+SUAT"],
        "direction": "credit",
    },
}


# =============================================================================
# LOOKUP HELPERS
# =============================================================================

def lookup_merchant(text: str) -> Optional[MerchantInfo]:
    """
    Look up a merchant from transaction description text.

    Performs case-insensitive substring matching against the merchant database.

    Args:
        text: Transaction description text.

    Returns:
        MerchantInfo if a match is found, None otherwise.
    """
    text_upper = text.upper()
    # Try exact match first (longer names first to avoid partial matches)
    for merchant_name in sorted(MERCHANT_DB.keys(), key=len, reverse=True):
        if merchant_name in text_upper:
            return MERCHANT_DB[merchant_name]
    return None


def get_merchants_by_category(category: str) -> List[str]:
    """Get all merchant names for a given category."""
    return [
        name for name, info in MERCHANT_DB.items()
        if info.category == category
    ]
