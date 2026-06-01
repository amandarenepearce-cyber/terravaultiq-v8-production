from typing import List
import pandas as pd


def normalize_zip_list(text: str) -> List[str]:
    if not text:
        return []
    parts = [p.strip() for p in str(text).replace("\n", ",").split(",")]
    return [p for p in parts if p]


def build_client_export_df(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "name",
        "business_type",
        "search_keyword",
        "source_zip",
        "address",
        "website",
        "primary_email",
        "primary_phone",
        "rating",
        "ratings_total",
        "lead_score",
        "lead_tier",
        "needs_leads_score",
        "needs_leads_tier",
        "needs_leads_reason",
        "ad_presence_status",
        "intent_topic",
        "pitch_opening_line",
        "pitch_offer",
        "pitch_cta",
    ]
    cols = [c for c in preferred if c in df.columns]
    remainder = [c for c in df.columns if c not in cols]
    return df[cols + remainder].copy()


def build_crm_export_df(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["name"] = df["name"] if "name" in df.columns else ""
    out["primary_email"] = df["primary_email"] if "primary_email" in df.columns else ""
    out["primary_phone"] = df["primary_phone"] if "primary_phone" in df.columns else (df["phone"] if "phone" in df.columns else "")
    out["website"] = df["website"] if "website" in df.columns else ""
    out["status"] = "new"
    out["priority"] = df["needs_leads_tier"] if "needs_leads_tier" in df.columns else ""
    out["owner"] = ""
    out["notes"] = df["pitch_reason"] if "pitch_reason" in df.columns else ""
    out["offer_angle"] = df["pitch_angle"] if "pitch_angle" in df.columns else ""
    out["follow_up_date"] = ""
    return out


def build_package_manifest(package_name: str, prepared_by: str, row_count: int, search_mode: str, keyword: str, area_label: str):
    return {
        "package_name": package_name,
        "prepared_by": prepared_by,
        "row_count": row_count,
        "search_mode": search_mode,
        "keyword": keyword,
        "area_label": area_label,
    }


def build_package_summary(package_name: str, prepared_by: str, row_count: int, search_mode: str, keyword: str, area_label: str):
    return (
        f"Package: {package_name}\n"
        f"Prepared by: {prepared_by}\n"
        f"Rows: {row_count}\n"
        f"Search mode: {search_mode}\n"
        f"Keyword: {keyword}\n"
        f"Area label: {area_label}\n"
    )
