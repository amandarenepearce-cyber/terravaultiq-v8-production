from __future__ import annotations

import html
import re
import time
from typing import Dict, Iterable, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 TerraVaultIQ/1.3",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT_SECONDS = 14
MAX_CONTACT_PAGES = 12
REQUEST_PAUSE_SECONDS = 0.15

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}")

CONTACT_HINTS = (
    "contact", "about", "team", "staff", "attorney", "attorneys", "lawyer", "lawyers",
    "people", "professionals", "locations", "office", "quote", "estimate", "consultation",
    "appointment", "request", "support", "service", "services", "leadership", "our-firm",
)

FALLBACK_PATHS = (
    "/contact", "/contact-us", "/about", "/about-us", "/team", "/staff", "/our-team",
    "/attorneys", "/attorney", "/lawyers", "/professionals", "/people", "/locations",
    "/office", "/offices", "/request-a-quote", "/free-estimate", "/get-a-quote",
)

BAD_EMAIL_PREFIXES = (
    "example@", "test@", "your@", "name@", "email@", "user@", "sentry@", "noreply@",
    "no-reply@", "donotreply@", "do-not-reply@", "privacy@", "abuse@", "postmaster@",
    "webmaster@", "root@", "admin@example",
)
BAD_EMAIL_DOMAINS = (
    "example.com", "example.org", "example.net", "domain.com", "email.com", "sentry.io",
    "wixpress.com", "squarespace.com", "wordpress.org", "schema.org", "godaddy.com",
)
BAD_EMAIL_SUBSTRINGS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", "@2x.",
    "@email.com", "@domain.com",
)


def normalize_website(url: str) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    url = url.replace(" ", "")
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def strip_tags(html_text: str) -> str:
    soup = BeautifulSoup(html_text or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _same_domain(base_url: str, href: str) -> bool:
    try:
        href_host = _host(href)
        return not href_host or href_host == _host(base_url)
    except Exception:
        return False


def _candidate_home_urls(url: str) -> list[str]:
    url = normalize_website(url)
    if not url:
        return []
    parsed = urlparse(url)
    host = parsed.netloc or parsed.path
    host = host.strip("/")
    if not host:
        return [url]
    bare = host.removeprefix("www.")
    candidates = [
        url,
        f"https://{bare}",
        f"https://www.{bare}",
        f"http://{bare}",
        f"http://www.{bare}",
    ]
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _clean_email(raw: str) -> str:
    email_value = html.unescape(str(raw or "")).strip().strip(".,;:()[]{}<>'\"|/")
    email_value = email_value.replace("mailto:", "")
    return email_value.lower()


def _is_good_email(email_value: str) -> bool:
    email_value = _clean_email(email_value)
    if not email_value or "@" not in email_value:
        return False
    if any(bad in email_value for bad in BAD_EMAIL_SUBSTRINGS):
        return False
    local, domain = email_value.rsplit("@", 1)
    if any(email_value.startswith(prefix) for prefix in BAD_EMAIL_PREFIXES):
        return False
    if domain in BAD_EMAIL_DOMAINS:
        return False
    if domain.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")):
        return False
    if len(local) < 2 or len(domain) < 4:
        return False
    if ".." in email_value:
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


def _decode_cloudflare_email(hex_string: str) -> str:
    try:
        data = bytes.fromhex(hex_string)
        key = data[0]
        decoded = "".join(chr(b ^ key) for b in data[1:])
        return _clean_email(decoded)
    except Exception:
        return ""


def _extract_cloudflare_emails(soup: BeautifulSoup) -> list[str]:
    emails: set[str] = set()
    for tag in soup.select(".__cf_email__"):
        encoded = tag.get("data-cfemail", "")
        decoded = _decode_cloudflare_email(encoded)
        if _is_good_email(decoded):
            emails.add(decoded)
    return sorted(emails)


def _extract_obfuscated_emails(text: str) -> list[str]:
    found: set[str] = set()
    normalized = html.unescape(text or "")
    normalized = normalized.replace("(a)", " at ").replace("[a]", " at ")
    patterns = [
        re.compile(r"([A-Za-z0-9._%+-]{2,})\s*(?:\[at\]|\(at\)|\sat\s|\sAT\s)\s*([A-Za-z0-9.-]+)\s*(?:\[dot\]|\(dot\)|\sdot\s|\sDOT\s)\s*([A-Za-z]{2,})", re.IGNORECASE),
        re.compile(r"([A-Za-z0-9._%+-]{2,})\s+at\s+([A-Za-z0-9.-]+)\.([A-Za-z]{2,})", re.IGNORECASE),
    ]
    for pattern in patterns:
        for local, domain, tld in pattern.findall(normalized):
            email_value = _clean_email(f"{local}@{domain}.{tld}")
            if _is_good_email(email_value):
                found.add(email_value)
    return sorted(found)


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


def _fetch_html(url: str) -> tuple[str, str, str]:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            return response.text, response.url, content_type
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.25 + attempt * 0.25)
    raise last_exc or RuntimeError("Website request failed")


def _fetch_homepage(url: str) -> tuple[str, str, str]:
    errors: list[str] = []
    for candidate in _candidate_home_urls(url):
        try:
            html_text, final_url, content_type = _fetch_html(candidate)
            if html_text:
                return html_text, final_url, content_type
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{candidate}: {exc}")
    raise RuntimeError("; ".join(errors[:3]) or "No homepage candidates worked")


def _extract_contact_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()

    def add_link(raw_url: str) -> None:
        if not raw_url:
            return
        absolute = urljoin(base_url, raw_url)
        if not _same_domain(base_url, absolute):
            return
        clean = absolute.split("#", 1)[0].rstrip("/")
        if clean and clean not in seen:
            links.append(clean)
            seen.add(clean)

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        label = a.get_text(" ", strip=True).lower()
        combined = f"{href} {label}".lower()
        if not href or href.startswith(("#", "tel:", "mailto:", "javascript:")):
            continue
        if any(hint in combined for hint in CONTACT_HINTS):
            add_link(href)

    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    for path in FALLBACK_PATHS:
        add_link(origin + path)

    return links[:MAX_CONTACT_PAGES]


def _extract_page_contact_data(page_url: str, html_text: str) -> dict:
    soup = BeautifulSoup(html_text or "", "html.parser")
    text = strip_tags(html_text)
    emails = _merge_unique(
        _extract_mailto_emails(soup)
        + _extract_cloudflare_emails(soup)
        + _extract_emails_from_text(html_text)
        + _extract_obfuscated_emails(text),
        limit=10,
    )
    phones = _merge_unique(PHONE_RE.findall(text), limit=5)
    has_form = bool(soup.find("form") or soup.find(attrs={"role": "form"}) or "contact form" in text.lower())
    return {"emails": emails, "phones": phones, "has_form": has_form, "soup": soup, "text": text}


def website_audit(url: str) -> Dict:
    url = normalize_website(url)
    empty_result = {
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
        "pages_scanned": 0,
        "scan_error": "",
    }
    if not url:
        return empty_result

    try:
        html_text, final_url, _content_type = _fetch_homepage(url)
    except Exception as e:
        result = dict(empty_result)
        result.update({
            "bad_website_score": 85,
            "website_notes": f"Website unavailable: {e}",
            "website_status": "down",
            "scan_error": str(e),
        })
        return result

    soup = BeautifulSoup(html_text, "html.parser")
    text = strip_tags(html_text)
    homepage_data = _extract_page_contact_data(final_url, html_text)

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag.get("content", "").strip() if meta_tag else ""
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    contact_links = _extract_contact_links(final_url, soup)
    contact_page_url = contact_links[0] if contact_links else ""
    contact_form_found = "yes" if homepage_data["has_form"] else "no"

    all_emails = list(homepage_data["emails"])
    phones = list(homepage_data["phones"])
    email_source_url = final_url if all_emails else ""
    page_notes: list[str] = []
    pages_scanned = 1

    for contact_url in contact_links:
        try:
            time.sleep(REQUEST_PAUSE_SECONDS)
            contact_html, resolved_contact_url, _ = _fetch_html(contact_url)
            pages_scanned += 1
            contact_data = _extract_page_contact_data(resolved_contact_url, contact_html)
            if contact_data["has_form"]:
                contact_form_found = "yes"
            if contact_data["emails"] and not email_source_url:
                email_source_url = resolved_contact_url
            all_emails.extend(contact_data["emails"])
            phones.extend(contact_data["phones"])
        except Exception as exc:  # noqa: BLE001
            page_notes.append(f"Skipped {contact_url}: {exc}")

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
    notes: list[str] = []
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
    notes.append(f"Scanned {pages_scanned} page(s)")
    notes.extend(page_notes[:2])

    offer_angle = ""
    text_lower = text.lower()
    if "free estimate" in text_lower or "request a quote" in text_lower:
        offer_angle = "Strong quote / estimate CTA detected"
    elif "apply now" in text_lower:
        offer_angle = "Application CTA detected"
    elif "contact us" in text_lower or "book now" in text_lower:
        offer_angle = "General lead capture CTA detected"

    email_confidence = "high" if emails and email_source_url and any(x in email_source_url.lower() for x in ["contact", "team", "staff", "about", "attorney"]) else "medium" if emails else "low"

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
        "pages_scanned": pages_scanned,
        "scan_error": "",
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
    if row.get("contact_form_found") == "yes":
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
