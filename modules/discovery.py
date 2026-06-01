import time
from typing import Dict, List, Tuple

import requests
import streamlit as st


HEADERS = {"User-Agent": "TerraVaultIQ/1.0"}

BUSINESS_PRESETS = {
    "roofing": "roofers",
    "roofers": "roofers",
    "cleaners": "cleaning companies",
    "cleaning": "cleaning companies",
    "house cleaners": "house cleaning service",
    "cleaning companies": "cleaning companies",
    "med spa": "med spas",
    "med spas": "med spas",
    "lawn care": "lawn care",
    "landscape lighting": "landscape lighting",
    "holiday lighting installer": "holiday lighting installer",
    "christmas light installation": "christmas light installation",
    "contractors": "contractors",
    "real estate": "real estate agents",
    "salons": "hair salons",
    "dentists": "dentists",
    "property managers": "property management",
    "apartments": "apartments",
    "plumbers": "plumbers",
    "electricians": "electricians",
    "painters": "painters",
    "restaurants": "restaurants",
    "mortgage lenders": "mortgage lenders",
    "credit unions": "credit unions",
    "loan officers": "loan officers",
}

def normalize_keyword(keyword: str) -> str:
    raw = str(keyword or "").strip().lower()
    return BUSINESS_PRESETS.get(raw, raw)

def geocode_google(api_key: str, place: str) -> Tuple[float, float, str]:
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place, "key": api_key}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Google Geocoding error: {data.get('status', 'unknown')}")

    result = data["results"][0]
    loc = result["geometry"]["location"]
    return loc["lat"], loc["lng"], result["formatted_address"]

def places_search(api_key: str, query: str, lat: float, lng: float, radius_m: int, max_pages: int = 3) -> List[dict]:
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    results = []
    next_page_token = None

    for _ in range(max_pages):
        params = {"query": query, "location": f"{lat},{lng}", "radius": radius_m, "key": api_key}
        if next_page_token:
            time.sleep(2.5)
            params = {"pagetoken": next_page_token, "key": api_key}

        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")

        if status not in ("OK", "ZERO_RESULTS"):
            if status == "INVALID_REQUEST" and next_page_token:
                continue
            raise ValueError(f"Google Places error: {status}")

        results.extend(data.get("results", []))
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

    return results

def get_place_details(api_key: str, place_id: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    fields = ",".join([
        "name",
        "website",
        "formatted_phone_number",
        "international_phone_number",
        "formatted_address",
        "url",
        "rating",
        "user_ratings_total",
        "types",
    ])
    params = {"place_id": place_id, "fields": fields, "key": api_key}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK":
        return {}
    return data.get("result", {})

def dedupe_rows(rows: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for row in rows:
        key = (
            str(row.get("name", "")).strip().lower(),
            str(row.get("address", "")).strip().lower(),
            str(row.get("website", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out

def discover_businesses(zip_code: str, radius: float, mode: str, keyword: str, use_google: bool, use_osm: bool) -> List[Dict]:
    api_key = st.session_state.get("google_api_key", "").strip()

    if not use_google or not api_key:
        return []

    search_keyword = normalize_keyword(keyword)
    area = zip_code.strip()
    radius_m = int(float(radius) * 1609.34)

    lat, lng, formatted_area = geocode_google(api_key, area)
    query = f"{search_keyword} in {formatted_area}"
    search_results = places_search(api_key, query, lat, lng, radius_m)

    rows = []
    for item in search_results:
        place_id = item.get("place_id", "")
        details = get_place_details(api_key, place_id) if place_id else {}

        rows.append({
            "name": details.get("name") or item.get("name", ""),
            "business_type": search_keyword,
            "search_keyword": search_keyword,
            "search_area": formatted_area,
            "address": details.get("formatted_address") or item.get("formatted_address", ""),
            "website": details.get("website", ""),
            "phone": details.get("formatted_phone_number") or details.get("international_phone_number", ""),
            "rating": details.get("rating", item.get("rating", "")),
            "ratings_total": details.get("user_ratings_total", item.get("user_ratings_total", "")),
            "google_maps_url": details.get("url", ""),
            "place_id": place_id,
            "types": ", ".join(details.get("types", item.get("types", []))),
        })

    return dedupe_rows(rows)

def search_public_topics(search_mode: str, keyword: str, zip_code: str, area_label: str, max_pages: int, use_google: bool, public_pages_only: bool) -> List[Dict]:
    return []

def expand_topic_queries(search_mode: str, keyword: str, zip_code: str = "", area_label: str = "") -> List[str]:
    base = str(keyword or "").strip()
    area = str(area_label or zip_code or "").strip()

    phrases = [
        f"{base} near me",
        f"best {base} {area}".strip(),
        f"{base} services {area}".strip(),
        f"top rated {base} {area}".strip(),
        f"affordable {base} {area}".strip(),
    ]

    return [p for p in phrases if p.strip()]
