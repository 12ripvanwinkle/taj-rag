"""
Scraper.py

This file exists for the sole reason of doing 2 things:
1. Download PDF files directly from TAJ (Tax administration of Jamaica) and saves them to the /documents folder
2. Fetche the html pages that contain tax content, strips the html tags and saves stripped text to the /documents as .txt files

"""
import os           # This library helps with file management, navigation
import time         # This library helps with handling time related operations such as adding delays between requests (polite scraping or else i will be seen as a threat)
import requests     # This library helps with making http requests (downloading pages/files)
from bs4 import BeautifulSoup       # This library helps with parsing html and extracting clean text
import re           # This library helps with searching for, match, and manipulate text based, in this case to lowercase everything
from urllib.parse import urljoin  # helps us convert relative URLs to absolute ones



# First Step: Configuration

# this is the section that deals with downloaded files (take the files and save them in /documents)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "documents")
# this line basically Goes to my folder

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
# This code dresses my Python request up like a normal human using Chrome. So i dont get blocked

# How long to wait between each request (in seconds).
# This is "polite scraping" — we don't hammer their server.
DELAY_SECONDS = 2
MAX_RETRIES = 3          
RETRY_WAIT = 5 

# ----------------------------------------------------------------

# Second Step: Scraping the Documents

# PDFS to Download
# Each entry is a tuple - ("filename_to_save_as.pdf", "full_url")
# These are the actual verified pdf links from the jamaicatax.gov.jm
BASE_URL = "https://www.jamaicatax.gov.jm"

# URLs to skip when scanning index pages.
# These appear as links on every single TAJ page (they're in the sidebar/footer)
# and are not relevant tax guidance documents.
URL_BLACKLIST = [
    "TAJ+10th+Anniversary",       # 6.7MB supplement, not tax guidance
    "taj-10th-anniversary",
    "property_tax_query",         # this is an image, not a document
    "garnishment_policy",         # already in our direct PDF list
]
 
# Global set to track which URLs we've already downloaded.
# This prevents downloading the same PDF multiple times when it
# appears as a link on multiple index pages.
downloaded_urls = set()

PDF_DOWNLOADS = [
    (
       "gct-quick-guide.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/21679950/GCT_Quick_Guide_to_GCT_%28Amended%29_032021.pdf/6a23364a-3cbe-ddb4-8de4-e9fb691af3e8" 
    ),
    (
        "gct-zero-rated-exempt-items.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/24445204/GCT_Zero_Rated_and_Exempt_Items_122020_2022.pdf/60eec7d3-a449-a1b3-88ac-6c5d3a7d6cd3"
    ),
    (
        "gct-advanced-guide.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/24445204/GCT+_ADVANCED_GCT_Document_%28amended%29_032021.pdf/d9bd3526-b29a-a617-5528-27063fddb678"
    ),
    (
        "gct-government-purchases-booklet.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/24445204/GCT_Govt_on_Government_Purchases_%28Booklet%29_Amended_032021.pdf/8d8601a8-b88d-cf6f-e85b-83c255f2aad3"
    ),
    (
        "gct-efiling-guide.pdf",
        "https://www.jamaicatax.gov.jm/documents/10181/531656/Filing+Your++Returns+Online.pdf/46322148-877d-4541-8ad6-67e98074cd81"
    ),
    (
        "garnishment-policy.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/8477881/garnishment_policy_042016.pdf/efbb26cd-36ad-fd21-3e38-f51d609a47db"
    ),
    (
        "tcc-application-form.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/19367/tcc_app_form.pdf/c8411cb3-348e-4957-a31d-0e341ce099b9"
    ),
    (
        "capital-allowance-schedule.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/18228/sch02.pdf/edf803b5-4afb-4a1f-b13d-2e4d4c8b38a2"
    ),
    (
        "income-tax-rates-thresholds-2013-2025.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/105112/copy-of-copy-of-income-tax-rates-thresholds-and-exemption-2013--2025-2nd-draft.pdf/6ed6065b-4bbb-12a3-0f10-57bb75947e82"
    ),
    (
        "capital-allowance-regime.pdf",
        "https://www.jamaicatax.gov.jm/documents/10194/31132/capital_allowance_regime2014.pdf/e6265e8e-d549-4eb8-8d84-e34d861cfa0f"
    ),
]

HTML_TEXT_PAGES = [
    (
        "self-employed-tax-guide.txt",
        "https://www.jamaicatax.gov.jm/self-employed/"
    ),
    (
        "rates-and-fees.txt",
        "https://www.jamaicatax.gov.jm/rates-and-fees/"
    ),
    (
        "trn-taxpayer-registration.txt",
        "https://www.jamaicatax.gov.jm/trn1"
    ),
    (
        "tcc-taxpayer-compliance-certificate.txt",
        "https://www.jamaicatax.gov.jm/tcc/"
    ),
    (
        "refunds.txt",
        "https://www.jamaicatax.gov.jm/refunds/"
    ),
    (
      "withholding-tax.txt",
      "https://www.jamaicatax.gov.jm/withholding-tax-hub"
    ),
]

# gives us almost nothing useful. Instead we:
#   1. Fetch the page
#   2. Find every link that points to a PDF
#   3. Download each of those PDFs
PDF_INDEX_PAGES = [
    (
        "payroll",
        "https://www.jamaicatax.gov.jm/web/guest/payroll"
        # Links to: employers guide, payroll taxes & contributions,
        # education tax, statutory remittance procedure
    ),
    (
        "income-tax",
        "https://www.jamaicatax.gov.jm/income-tax"
        # Links to: income tax for individuals/businesses, rates & thresholds,
        # contracts, non-residents, pensioners, school leavers
    ),
    (
        "tcc-publications",
        "https://www.jamaicatax.gov.jm/tax-compliance-certificate-tcc-"
        # Links to: TCC guides and publications
    ),
    (
        "trn-publications",
        "https://www.jamaicatax.gov.jm/taxpayer-registration-number"
        # Links to: TRN requirement sheets
    ),
]

# ----------------------------------------------------------------

# Section 3: Helper functions

# Before putting stuff in Foler, make sure the folder actually exists, if not it creates it
def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output folder ready: {OUTPUT_DIR}\n")


# This function cleans ugly text and turns it into a safe filename.
# Such as lowercase everything, 
# replace any character that isnt alphanumeric or dot with a hyphen, 
# collapse multiple hyphens into one
# and remove leading/trailing hyphens
def make_safe_filename(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    
    return text


def is_blacklisted(url):
    
    for pattern in URL_BLACKLIST:
        if pattern.lower() in url.lower():
            return True
    return False

# Internet fail sometimes. Don’t give up immediately. Try multiple times before crying
def fetch_with_retry(url, stream=False):
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                stream=stream,
                timeout=30
            )
            if response.status_code == 200:
                return response
            else:
                print(f"  [!] HTTP {response.status_code} on attempt {attempt}/{MAX_RETRIES}")
        except requests.exceptions.RequestException as e:
            print(f"  [!] Attempt {attempt}/{MAX_RETRIES} failed: {type(e).__name__}")
 
        # Don't wait after the last attempt
        if attempt < MAX_RETRIES:
            print(f"  [→] Waiting {RETRY_WAIT}s before retry...")
            time.sleep(RETRY_WAIT)
 
    return None  # all retries exhausted

# This function downloads a PDF from the internet and saves it into your documents folder.
# it uses stream=True to download in 4KB chunks — safe for large files without loading everything into RAM first.
# If PDF not already in Folder, go internet, grab it piece-by-piece, and store safely.

def download_pdf(filename, url):
    """Downloads a single PDF and saves it to /documents/."""
    # Mark this URL as downloaded so index pages don't re-download it
    downloaded_urls.add(url)
 
    save_path = os.path.join(OUTPUT_DIR, filename)
 
    if os.path.exists(save_path):
        print(f"  [SKIP] Already exists: {filename}")
        return
 
    if is_blacklisted(url):
        print(f"  [SKIP] Blacklisted: {filename}")
        return
 
    print(f"  [PDF] Downloading: {filename}")
 
    response = fetch_with_retry(url, stream=True)
 
    if response:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=4096):
                f.write(chunk)
        size_kb = os.path.getsize(save_path) / 1024
        print(f"  [✓] Saved ({size_kb:.1f} KB)")
    else:
        print(f"  [✗] Failed after {MAX_RETRIES} attempts — skipping")
 
# Website messy. Remove trash. Search all rooms. Keep room with most useful words.
def extract_main_content(soup, url):
   
    # Remove noise elements first
    for tag in soup.find_all(["nav", "script", "style", "footer",
                               "header", "noscript"]):
        tag.decompose()
 
    # List of candidate selectors to try, in order of preference
    # We try all of them and keep the one that gives the most text
    candidates = [
        soup.find("div", class_="portlet-body"),
        soup.find("div", class_="journal-content-article"),
        soup.find("div", class_="portlet-content"),
        soup.find("div", {"id": "main-content"}),
        soup.find("main"),
        soup.find("article"),
        soup.find("div", class_="content"),
        soup.body,  # last resort — entire body
    ]
 
    best_text = ""
 
    for candidate in candidates:
        if candidate is None:
            continue
        text = candidate.get_text(separator="\n", strip=True)
        # Keep whichever candidate gave us the most text
        if len(text) > len(best_text):
            best_text = text
 
    # Clean up excessive blank lines
    lines = best_text.splitlines()
    cleaned = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned.append("")
        else:
            blank_count = 0
            cleaned.append(line)
 
    return "\n".join(cleaned).strip()


# Go website. Ignore shiny useless decorations. Take important words only. Save words in Document.

def scrape_html_page(filename, url):
    """Fetches an HTML page and saves it as clean text."""
    save_path = os.path.join(OUTPUT_DIR, filename)
 
    if os.path.exists(save_path):
        print(f"  [SKIP] Already exists: {filename}")
        return
 
    print(f"  [HTML→TXT] Scraping: {filename}")
 
    response = fetch_with_retry(url)
 
    if not response:
        print(f"  [✗] Failed after {MAX_RETRIES} attempts")
        return
 
    soup = BeautifulSoup(response.text, "html.parser")
    clean_text = extract_main_content(soup, url)
 
    if not clean_text:
        print(f"  [✗] No content found on page")
        return
 
    final_text = f"SOURCE: {url}\n\n{clean_text}"
 
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(final_text)
 
    word_count = len(clean_text.split())
    print(f"  [✓] Saved ({word_count:,} words)")

# THis function Go page. Find all PDFs. Name them. Bring them home.
def scrape_pdf_index_page(prefix, url):

    print(f"\n  [INDEX] Scanning: {url}")
 
    response = fetch_with_retry(url)
    if not response:
        print(f"  [✗] Failed to load index page")
        return
 
    soup = BeautifulSoup(response.text, "html.parser")
    all_links = soup.find_all("a", href=True)
 
    # Find all links to TAJ document PDFs
    pdf_links = []
    seen_urls = set()
    for link in all_links:
        href = link["href"]
        full_url = urljoin(BASE_URL, href)
 
        # Only keep /documents/ links, and deduplicate within this page
        if "/documents/" in full_url and full_url not in seen_urls:
            seen_urls.add(full_url)
            pdf_links.append((link.get_text(strip=True), full_url))
 
    if not pdf_links:
        print(f"  [!] No PDF links found")
        return
 
    # Count how many we'll actually download (after filtering)
    to_download = [
        (text, u) for text, u in pdf_links
        if u not in downloaded_urls and not is_blacklisted(u)
    ]
 
    print(f"  [✓] Found {len(pdf_links)} PDF link(s), "
          f"{len(to_download)} new to download")
 
    for link_text, pdf_url in pdf_links:
        # Skip if already downloaded from a previous index page
        if pdf_url in downloaded_urls:
            print(f"  [SKIP] Already downloaded from another page")
            continue
 
        # Skip blacklisted files
        if is_blacklisted(pdf_url):
            print(f"  [SKIP] Blacklisted URL")
            downloaded_urls.add(pdf_url)  # mark so we don't try again
            continue
 
        # Build filename from link text + prefix
        if link_text:
            raw_name = f"{prefix}-{link_text}.pdf"
        else:
            raw_name = f"{prefix}-{pdf_url.split('/')[-2]}.pdf"
 
        filename = make_safe_filename(raw_name)
        download_pdf(filename, pdf_url)
        time.sleep(DELAY_SECONDS)


# ----------------------------------------------------------------
# Section 4: main execution

def main():
    print("=" * 60)
    print("  TAJ Document Collector — taj-rag")
    print("=" * 60)
    print()

    ensure_output_dir()

    # phase 1: Direct pdf downloads
    print(f"PHASE 1: Direct PDF downloads ({len(PDF_DOWNLOADS)} files)")
    print("-" * 40)
    for filename, url in PDF_DOWNLOADS:
        download_pdf(filename, url)
        time.sleep(DELAY_SECONDS)

    # phase 2: HTML Pages -> save as text
    print(f"\nPHASE 2: HTML pages → text files ({len(HTML_TEXT_PAGES)} pages)")
    print("-" * 40)
    for filename, url in HTML_TEXT_PAGES:
        scrape_html_page(filename, url)
        time.sleep(DELAY_SECONDS)

    # Phase 3: Index pages -> find and download their pdfs
    print(f"\nPHASE 3: PDF index pages ({len(PDF_INDEX_PAGES)} pages to scan)")
    print("-" * 40)
    for prefix, url in PDF_INDEX_PAGES:
        scrape_pdf_index_page(prefix, url)
        time.sleep(DELAY_SECONDS)
    
    # Summary 
    print("\n" + "=" * 60)
    print("  Collection complete!")
    print("=" * 60)

    all_files = os.listdir(OUTPUT_DIR)
    pdfs = [f for f in all_files if f.endswith(".pdf")]
    txts = [f for f in all_files if f.endswith(".txt")]

    print(f"\n  PDFs collected : {len(pdfs)}")
    print(f"  Text files     : {len(txts)}")
    print(f"  Total documents: {len(pdfs) + len(txts)}")
    print(f"\n  Saved to: {OUTPUT_DIR}")
    print("\n  ✓ Chapter 2 complete. Ready for Chapter 3 (ingestion pipeline).")


if __name__ == "__main__":
    main()