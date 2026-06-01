import re
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "TerraVaultIQ/1.0"}


def normalize_website(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def strip_tags(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return " ".join(soup.stripped_strings)


def website_audit(url: str) -> Dict:
    url = normalize_website(url)
    if not url:
        return {
            "site_live": "no",
            "final_url": "",
            "emails_found": "",
            "phones_found": "",
            "facebook_link": "",
            "instagram_link": "",
            "linkedin_link": "",
            "title": "",
            "meta_description": "",
            "h1": "",
            "bad_website_score": 100,
            "website_notes": "No website found.",
            "offer_angle": "",
            "website_status": "missing",
        }

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text
        final_url = r.url
    except Exception as e:
        return {
            "site_live": "no",
            "final_url": "",
            "emails_found": "",
            "phones_found": "",
            "facebook_link": "",
            "instagram_link": "",
            "linkedin_link": "",
            "title": "",
            "meta_description": "",
            "h1": "",
            "bad_website_score": 85,
            "website_notes": f"Website unavailable: {e}",
            "offer_angle": "",
            "website_status": "down",
        }

    soup = BeautifulSoup(html, "html.parser")
    text = strip_tags(html)

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag.get("content", "").strip() if meta_tag else ""
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)))
    phones = sorted(set(re.findall(r"(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}", text)))

    facebook = ""
    instagram = ""
    linkedin = ""

    for a in soup.find_all("a", href=True):
        href = a["href"]
        low = href.lower()
        if "facebook.com" in low and not facebook:
            facebook = href
        elif "instagram.com" in low and not instagram:
            instagram = href
        elif "linkedin.com" in low and not linkedin:
            linkedin = href

    bad_score = 0
    notes = []

    if not title:
        bad_score += 20
        notes.append("Missing title")
    if not meta_description:
        bad_score += 10
        notes.append("Missing meta description")
    if not h1:
        bad_score += 10
        notes.append("Missing H1")
    if not emails:
        bad_score += 10
        notes.append("No public email found")
    if not phones:
        bad_score += 8
        notes.append("No phone found on site")
    if not (facebook or instagram or linkedin):
        bad_score += 6
        notes.append("No socials found")

    offer_angle = ""
    text_lower = text.lower()
    if "free estimate" in text_lower or "request a quote" in text_lower:
        offer_angle = "Strong quote / estimate CTA detected"
    elif "apply now" in text_lower:
        offer_angle = "Application CTA detected"
    elif "contact us" in text_lower or "book now" in text_lower:
        offer_angle = "General lead capture CTA detected"

    return {
        "site_live": "yes",
        "final_url": final_url,
        "emails_found": ", ".join(emails[:5]),
        "phones_found": ", ".join(phones[:5]),
        "facebook_link": facebook,
        "instagram_link": instagram,
        "linkedin_link": linkedin,
        "title": title,
        "meta_description": meta_description,
        "h1": h1,
        "bad_website_score": bad_score,
        "website_notes": "; ".join(notes) if notes else "Website appears usable.",
        "offer_angle": offer_angle,
        "website_status": "live",
    }


def infer_contact_confidence(row: Dict) -> str:
    score = 0
    if row.get("primary_email"):
        score += 2
    if row.get("primary_phone"):
        score += 1
    if row.get("website"):
        score += 1
    if row.get("facebook_link") or row.get("instagram_link") or row.get("linkedin_link"):
        score += 1

    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def enrich_rows(rows: List[Dict]) -> List[Dict]:
    enriched = []

    for row in rows:
        item = dict(row)
        website = item.get("website", "") or item.get("final_url", "")
        audit = website_audit(website)

        item.update(audit)

        emails = [e.strip() for e in str(audit.get("emails_found", "")).split(",") if e.strip()]
        phones = [p.strip() for p in str(audit.get("phones_found", "")).split(",") if p.strip()]

        item["primary_email"] = emails[0] if emails else ""
        item["secondary_email"] = emails[1] if len(emails) > 1 else ""
        item["primary_phone"] = phones[0] if phones else item.get("phone", "")
        item["contact_confidence"] = infer_contact_confidence(item)

        enriched.append(item)

    return enriched
