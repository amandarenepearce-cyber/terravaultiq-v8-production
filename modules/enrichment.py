from __future__ import annotations

import html
import re
from typing import Dict, Iterable, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TerraVaultIQ/1.2; +https://terravaultiq.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT_SECONDS = 12
MAX_CONTACT_PAGES = 5

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}")

CONTACT_HINTS = (
    "contact",
    "about",
    "team",
    "staff",
    "attorney",
    "lawyer",
    "locations",
    "office",
    "quote",
    "estimate",
    "consultation",
)

BAD_EMAIL_PREFIXES = (
    "example@",
    "test@",
    "your@",
    "name@",
    "email@",
    "user@",
    "sentry@",
    "noreply@",
    "no-reply@",
    "donotreply@",
)

BAD_EMAIL_DOMAINS = (
    "example.com",
    "example.org",
    "example.net",
    "domain.com",
    "email.com",
    "sentry.io",
)


def normalize_website(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def strip_tags(html_text: str) -> str:
    soup = BeautifulSoup(html_text or "", "html.parser")
    return " ".join(soup.stripped_strings)


def _same_domain(base_url: str, href: str) -> bool:
    try:
        base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
        href_host = urlparse(href).netloc.lower().removeprefix("www.")
        return not href_host or href_host == base_host
    except Exception:
        return False


def _clean_email(raw: str) -> str:
    email_value = html.unescape(str(raw or "")).strip().strip(".,;:()[]{}<>'\"")
    return email_value.lower()


def _is_good_email(email_value: str) -> bool:
    email_value = _clean_email(email_value)
    if not email_value or "@" not in email_value:
        return False
    local, domain = email_value.rsplit("@", 1)
    if any(email_value.startswith(prefix) for prefix in BAD_EMAIL_PREFIXES):
        return False
    if domain in BAD_EMAIL_DOMAINS:
        return False
    if domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
        return False
    if len(local) < 2 or len(domain) < 4:
        return False
    return True


def _extract_emails_from_text(text: str) -> list[str]:
    candidates = {_clean_email(match) for match in EMAIL_RE.findall(text or "")}
    return sorted(email for email in candidates if _is_good_email(email))


def _extract_mailto_emails(soup: BeautifulSoup) -> list[str]:
    emails: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = html.unescape(a.get("href", ""))
        if href.lower().startswith("mailto:"):
            email_part = href.split(":", 1)[1].split("?", 1)[0]
            for value in EMAIL_RE.findall(email_part):
                cleaned = _clean_email(value)
                if _is_good_email(cleaned):
                    emails.add(cleaned)
    return sorted(emails)


def _extract_obfuscated_emails(text: str) -> list[str]:
    """Catch common public obfuscations like info [at] domain [dot] com."""
    found: set[str] = set()
    normalized = html.unescape(text or "")
    pattern = re.compile(
        r"([A-Za-z0-9._%+-]{2,})\s*(?:\[at\]|\(at\)|\sat\s)\s*([A-Za-z0-9.-]+)\s*(?:\[dot\]|\(dot\)|\sdot\s)\s*([A-Za-z]{2,})",
        re.IGNORECASE,
    )
    for local, domain, tld in pattern.findall(normalized):
        email_value = _clean_email(f"{local}@{domain}.{tld}")
        if _is_good_email(email_value):
            found.add(email_value)
    return sorted(found)


def _extract_contact_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        label = a.get_text(" ", strip=True).lower()
        combined = f"{href} {label}".lower()
        if not href or href.startswith(("#", "tel:", "mailto:", "javascript:")):
            continue
        if not any(hint in combined for hint in CONTACT_HINTS):
            continue
        absolute = urljoin(base_url, href)
        if not _same_domain(base_url, absolute):
            continue
        clean = absolute.split("#", 1)[0]
        if clean not in seen:
            links.append(clean)
            seen.add(clean)
        if len(links) >= MAX_CONTACT_PAGES:
            break
    return links


def _fetch_html(url: str) -> tuple[str, str, str]:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, allow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type and content_type:
        return response.text, response.url, content_type
    return response.text, response.url, content_type


def _merge_unique(values: Iterable[str], limit: int = 10) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned.lower() in seen:
            continue
        out.append(cleaned)
        seen.add(cleaned.lower())
        if len(out) >= limit:
            break
    return out


def website_audit(url: str) -> Dict:
    url = normalize_website(url)
    if not url:
        return {
            "site_live": "no",
            "final_url": "",
            "emails_found": "",
            "primary_email": "",
            "secondary_email": "",
            "email_found": "no",
            "email_source_url": "",
            "email_confidence": "low",
            "contact_page_url": "",
            "contact_form_found": "no",
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
        html_text, final_url, _content_type = _fetch_html(url)
    except Exception as e:
        return {
            "site_live": "no",
            "final_url": "",
            "emails_found": "",
            "primary_email": "",
            "secondary_email": "",
            "email_found": "no",
            "email_source_url": "",
            "email_confidence": "low",
            "contact_page_url": "",
            "contact_form_found": "unknown",
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

    soup = BeautifulSoup(html_text, "html.parser")
    text = strip_tags(html_text)

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag.get("content", "").strip() if meta_tag else ""
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    homepage_emails = _merge_unique(_extract_mailto_emails(soup) + _extract_emails_from_text(html_text) + _extract_obfuscated_emails(text))
    phones = _merge_unique(PHONE_RE.findall(text), limit=5)

    contact_links = _extract_contact_links(final_url, soup)
    contact_page_url = contact_links[0] if contact_links else ""
    contact_form_found = "yes" if soup.find("form") else "no"

    email_source_url = final_url if homepage_emails else ""
    all_emails = list(homepage_emails)
    page_notes: list[str] = []

    for contact_url in contact_links:
        try:
            contact_html, resolved_contact_url, _ = _fetch_html(contact_url)
            contact_soup = BeautifulSoup(contact_html, "html.parser")
            contact_text = strip_tags(contact_html)
            contact_emails = _merge_unique(
                _extract_mailto_emails(contact_soup)
                + _extract_emails_from_text(contact_html)
                + _extract_obfuscated_emails(contact_text),
                limit=10,
            )
            if contact_soup.find("form"):
                contact_form_found = "yes"
            if contact_emails and not email_source_url:
                email_source_url = resolved_contact_url
            all_emails.extend(contact_emails)
            phones.extend(PHONE_RE.findall(contact_text))
        except Exception as exc:  # noqa: BLE001
            page_notes.append(f"Could not scan contact page {contact_url}: {exc}")

    emails = _merge_unique(all_emails, limit=10)
    phones = _merge_unique(phones, limit=5)

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
    if contact_form_found == "yes" and not emails:
        notes.append("Contact form found but no public email displayed")
    if not (facebook or instagram or linkedin):
        bad_score += 6
        notes.append("No socials found")
    notes.extend(page_notes[:2])

    offer_angle = ""
    text_lower = text.lower()
    if "free estimate" in text_lower or "request a quote" in text_lower:
        offer_angle = "Strong quote / estimate CTA detected"
    elif "apply now" in text_lower:
        offer_angle = "Application CTA detected"
    elif "contact us" in text_lower or "book now" in text_lower:
        offer_angle = "General lead capture CTA detected"

    email_confidence = "high" if emails and email_source_url and "contact" in email_source_url.lower() else "medium" if emails else "low"

    return {
        "site_live": "yes",
        "final_url": final_url,
        "emails_found": ", ".join(emails[:10]),
        "primary_email": emails[0] if emails else "",
        "secondary_email": emails[1] if len(emails) > 1 else "",
        "email_found": "yes" if emails else "no",
        "email_source_url": email_source_url,
        "email_confidence": email_confidence,
        "contact_page_url": contact_page_url,
        "contact_form_found": contact_form_found,
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
        score += 3
    if row.get("email_source_url"):
        score += 1
    if row.get("primary_phone"):
        score += 1
    if row.get("website"):
        score += 1
    if row.get("facebook_link") or row.get("instagram_link") or row.get("linkedin_link"):
        score += 1

    if score >= 5:
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

        emails = [e.strip() for e in str(item.get("emails_found", "")).split(",") if e.strip()]
        phones = [p.strip() for p in str(item.get("phones_found", "")).split(",") if p.strip()]

        item["primary_email"] = item.get("primary_email") or (emails[0] if emails else "")
        item["secondary_email"] = item.get("secondary_email") or (emails[1] if len(emails) > 1 else "")
        item["primary_phone"] = phones[0] if phones else item.get("phone", "")
        item["email_found"] = "yes" if item.get("primary_email") else "no"
        item["contact_confidence"] = infer_contact_confidence(item)

        enriched.append(item)

    return enriched
