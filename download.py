
import argparse
import json
import logging
import re
import uuid
import urllib.parse
import urllib3
from tempfile import gettempdir
from datetime import datetime, timedelta
from pathlib import Path
import threading
import concurrent.futures
import os

import requests
from bs4 import BeautifulSoup
import lxml.html as LH
import easyocr

from typing import Optional, Tuple, Dict
from gcs_utils import upload_to_gcs

# ─── Setup & Constants ─────────────────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_URL            = "https://judgments.ecourts.gov.in"
SEARCH_URL          = f"{ROOT_URL}/pdfsearch/?p=pdf_search/home/"
CAPTCHA_URL         = f"{ROOT_URL}/pdfsearch/vendor/securimage/securimage_show.php"
CAPTCHA_TOKEN_URL   = f"{ROOT_URL}/pdfsearch/?p=pdf_search/checkCaptcha"
PDF_LINK_URL        = f"{ROOT_URL}/pdfsearch/?p=pdf_search/openpdfcaptcha"
PDF_LINK_WO_CAPTCHA = f"{ROOT_URL}/pdfsearch/?p=pdf_search/openpdf"

OUTPUT_DIR         = Path("ecourts-data")
TRACK_FILE         = Path("track.json")
COURT_CODES_FILE   = Path("court-codes.json")
CAPTCHA_TMP_DIR    = Path(gettempdir()) / "ecourts-captcha-tmp"
CAPTCHA_FAIL_DIR   = Path("captcha-failures")

START_DATE         = "2008-01-01"
PAGE_SIZE          = 1000
NO_CAPTCHA_BATCH   = 25

PAYLOAD = (
    "&sEcho=1&iColumns=2&sColumns=,&iDisplayStart=0&iDisplayLength=100&mDataProp_0=0"
    "&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true"
    "&mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true"
    "&sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=asc&iSortingCols=1"
    "&search_txt1=&search_txt2=&search_txt3=&search_txt4=&search_txt5="
    "&pet_res=&state_code=&state_code_li=&dist_code=null&case_no="
    "&case_year=&from_date=&to_date=&judge_name=®_year=&fulltext_case_type="
    "&int_fin_party_val=undefined&int_fin_case_val=undefined&int_fin_court_val=undefined"
    "&int_fin_decision_val=undefined&act=&sel_search_by=undefined§ions=undefined"
    "&judge_txt=&act_txt=§ion_txt=&judge_val=&act_val=&year_val=&judge_arr=&flag="
    "&disp_nature=&search_opt=PHRASE&date_val=ALL&fcourt_type=2&citation_yr=&citation_vol="
    "&citation_supl=&citation_page=&case_no1=&case_year1=&pet_res1=&fulltext_case_type1="
    "&citation_keyword=&sel_lang=&proximity=&neu_cit_year=&neu_no=&ajax_req=true"
)
PDF_LINK_PAYLOAD = (
    "val=0&lang_flg=undefined&path=&page=&search=+&citation_year=&fcourt_type=2"
    "&file_type=undefined&nc_display=undefined&ajax_req=true"
)

_track_lock = threading.Lock()
reader = easyocr.Reader(["en"])

# Create directories with proper permissions
try:
    CAPTCHA_TMP_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
    CAPTCHA_FAIL_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True, mode=0o755)
except PermissionError as e:
    logger.error(f"Failed to create directories: {e}")
    raise

# ─── Utility Functions ─────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^\w]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

def get_json(path: Path) -> Dict:
    return json.loads(path.read_text()) if path.exists() else {}

def save_json(path: Path, data: Dict):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    path.write_text(json.dumps(data, indent=2))
    path.chmod(0o644)

def get_tracking_data() -> Dict:
    return get_json(TRACK_FILE)

def save_tracking_data(d: Dict):
    save_json(TRACK_FILE, d)

def save_court_tracking(court_code: str, tracking: Dict):
    with _track_lock:
        all_ = get_tracking_data()
        all_[court_code] = tracking
        save_tracking_data(all_)

def get_court_codes() -> Dict:
    return get_json(COURT_CODES_FILE)

def get_new_date_range(last_date: str, step: int=1) -> Tuple[Optional[str], Optional[str]]:
    last = datetime.strptime(last_date, "%Y-%m-%d")
    start = last + timedelta(days=1)
    end   = start + timedelta(days=step-1)
    today = datetime.now().date()
    if start.date() > today:
        return None, None
    if end.date() > today:
        end = today
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def date_ranges(court_code: str,
                start_date: Optional[str]=None,
                end_date: Optional[str]=None,
                step: int=1):
    if start_date and not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date and end_date:
        s, e = datetime.strptime(start_date, "%Y-%m-%d"), datetime.strptime(end_date, "%Y-%m-%d")
        cur = s
        while cur <= e:
            r_end = min(cur + timedelta(days=step-1), e)
            yield cur.strftime("%Y-%m-%d"), r_end.strftime("%Y-%m-%d")
            cur = r_end + timedelta(days=1)
    else:
        track = get_tracking_data().get(court_code, {})
        last  = track.get("last_date", START_DATE)
        cur   = datetime.strptime(last, "%Y-%m-%d") + timedelta(days=1)
        e     = datetime.now()
        while cur <= e:
            r_end = min(cur + timedelta(days=step-1), e)
            yield cur.strftime("%Y-%m-%d"), r_end.strftime("%Y-%m-%d")
            cur = r_end + timedelta(days=1)

# ─── Task Orchestration ────────────────────────────────────────────────────────

class CourtDateTask:
    def __init__(self, court_code: str, frm: str, to: str):
        self.id = str(uuid.uuid4())
        self.court_code = court_code
        self.frm = frm
        self.to = to

    def __str__(self):
        return f"{self.court_code} {self.frm}->{self.to} [{self.id}]"

def generate_tasks(codes: list[str], start_date, end_date, step):
    all_codes = get_court_codes()
    for code in codes:
        if code not in all_codes:
            raise ValueError(f"Unknown court code {code}")
        for frm, to in date_ranges(code, start_date, end_date, step):
            yield CourtDateTask(code, frm, to)

def process_task(task: CourtDateTask):
    logger.info(f"▶ Starting {task}")
    try:
        dl = Downloader(task.court_code)
        dl.process_date_range(task.frm, task.to)
    except Exception:
        logger.error(f"❌ Failed {task}:", exc_info=True)

def run(codes, start_date, end_date, step, workers):
    tasks = list(generate_tasks(codes, start_date, end_date, step))
    if not tasks:
        logger.info("No tasks to run.")
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for i, _ in enumerate(pool.map(process_task, tasks), 1):
            logger.info(f"✅ Completed task {i}/{len(tasks)}")
    logger.info("✅ All done.")

# ─── Downloader ───────────────────────────────────────────────────────────────

class Downloader:
    def __init__(self, court_code: str):
        self.code = court_code
        self.name = get_court_codes()[court_code]
        self.tracking = get_tracking_data().get(court_code, {})
        self.session = requests.Session()
        self.app_token = None

    def init_session(self):
        self.session.cookies.clear()
        r = self.session.get(f"{ROOT_URL}/pdfsearch/",
                             headers={"User-Agent": "Mozilla/5.0"},
                             verify=False, timeout=30)
        if not self.session.cookies.get("JSESSION"):
            raise RuntimeError("Failed to init session")

    def headers(self) -> Dict:
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": ROOT_URL,
            "Referer": ROOT_URL,
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
        }

    def solve_math(self, expr: str) -> str:
        expr = expr.replace("×", "*").replace("X", "*").replace("x", "*").replace("÷", "/")
        for op in "+-*/":
            if op in expr:
                a, b = expr.split(op)
                return str(int(a) + int(b) if op == "+" else
                           int(a) - int(b) if op == "-" else
                           int(a) * int(b) if op == "*" else
                           int(a) // int(b))
        raise ValueError("Bad captcha")

    def solve_captcha(self, retries=0) -> str:
        if retries > 5:
            raise RuntimeError("Captcha fail")
        try:
            r = self.session.get(CAPTCHA_URL, verify=False, timeout=30)
            r.raise_for_status()
            
            img_id = uuid.uuid4().hex[:8]
            tmp = CAPTCHA_TMP_DIR / f"{self.code}_{img_id}.png"
            
            # Secure file write with proper permissions
            tmp.touch(mode=0o600, exist_ok=True)
            tmp.write_bytes(r.content)
            tmp.chmod(0o644)  # Readable by all after write
            
            res = reader.readtext(str(tmp))
            tmp.unlink(missing_ok=True)  # Cleanup immediately
            
            if not res:
                if retries > 5:
                    raise ValueError("Bad captcha (max retries exceeded)")
                
            txt = res[0][1].strip()
            if re.search(r"[0-9\+\-\*\/]", txt):
                return self.solve_math(txt)
                
            return self.solve_captcha(retries + 1)
            
        except Exception as e:
            logger.error(f"CAPTCHA processing failed: {e}")
            raise

    def refresh_token(self, use_app=False):
        ans = self.solve_captcha()
        data = {"captcha": ans, "search_opt": "PHRASE", "ajax_req": "true"}
        if use_app and self.app_token:
            data["app_token"] = self.app_token
        r = self.session.post(CAPTCHA_TOKEN_URL, headers=self.headers(),
                              data=data, verify=False, timeout=60)
        self.app_token = r.json().get("app_token")

    def request_api(self, method, url, data):
        r = self.session.request(method, url, headers=self.headers(),
                                 data=data, verify=False, timeout=60)
        try:
            j = r.json()
        except:
            j = {}
        if "app_token" in j:
            self.app_token = j["app_token"]
        if "filename" in j and "securimage_show" in j["filename"]:
            tree = LH.fromstring(j["filename"])
            src = tree.xpath("//img[@id='captcha_image_pdf']/@src")[0]
            ans = self.solve_captcha()
            data.update({"captcha1": ans, "app_token": j["app_token"]})
            return self.session.post(PDF_LINK_WO_CAPTCHA, headers=self.headers(),
                                     data=data, verify=False, timeout=60)
        if j.get("session_expire") == "Y" or "errormsg" in j:
            self.refresh_token(use_app=True)
            data["app_token"] = self.app_token
            return self.request_api(method, url, data)
        return r

    def default_search_payload(self) -> Dict:
        qs = urllib.parse.parse_qs(PAYLOAD.lstrip("&"))
        out = {k: v[0] for k, v in qs.items()}
        out.update({"sEcho": 1, "iDisplayStart": 0, "iDisplayLength": PAGE_SIZE})
        return out

    def default_pdf_payload(self) -> Dict:
        qs = urllib.parse.parse_qs(PDF_LINK_PAYLOAD)
        return {k: v[0] for k, v in qs.items()}

    def get_pdf_path(self, frag: str, frm: str, to: str) -> Path:
        year_m = re.search(r"/(\d{4})/", frag)
        year = year_m.group(1) if year_m else frm[:4]
        slug = slugify(self.name)
        fn = Path(frag).name
        return OUTPUT_DIR / self.code / slug / year / f"{frm}_{to}" / fn

    def get_meta_path(self, frag: str, frm: str, to: str) -> Path:
        return self.get_pdf_path(frag, frm, to).with_suffix(".json")

    def already_downloaded(self, frag: str, frm: str, to: str) -> bool:
        return self.get_meta_path(frag, frm, to).exists()

    def _parse_metadata(self, html: str) -> Dict:
        tree = LH.fromstring(html)
        title = "".join(tree.xpath("//button//text()")).strip()
        desc = " ".join(t.strip() for t in tree.xpath("//button/text()") if t.strip())
        judge = ""
        for s in tree.xpath("//strong/text()"):
            if "Judge" in s or "Hon'ble" in s:
                judge = s.split(":", 1)[-1].strip()
                break
        cd = tree.xpath('//strong[@class="caseDetailsTD"]')
        details = {"cnr": "", "date_reg": "", "date_dec": "", "disp": ""}
        if cd:
            block = cd[0]
            def ex(label):
                r = block.xpath(f'.//span[contains(text(), "{label}")]/following-sibling::font/text()')
                return r[0].strip() if r else ""
            details = {
                "cnr": ex("CNR"),
                "date_reg": ex("Date of registration"),
                "date_dec": ex("Decision Date"),
                "disp": ex("Disposal Nature"),
            }
        return {"title": title, "description": desc, "judge": judge, **details}

    def process_date_range(self, frm: str, to: str):
        if not (frm and to):
            return
        logger.info(f"Processing {self.code} {frm}->{to}")
        sp = self.default_search_payload()
        sp.update({"from_date": frm, "to_date": to, "state_code": self.code, "app_token": self.app_token or ""})

        self.init_session()
        downloaded_count = 0
        more = True

        while more:
            resp = self.request_api("POST", SEARCH_URL, sp)
            data = resp.json()
            rows = data.get("reportrow", {}).get("aaData", [])
            if not rows:
                more = False
                self.tracking["last_date"] = to
                save_court_tracking(self.code, self.tracking)
                logger.info(f"Updated track for {self.code}→{to}")
                break

            for idx, row in enumerate(rows):
                try:
                    self._handle_row(row, idx, frm, to)
                    downloaded_count += 1
                    if downloaded_count >= NO_CAPTCHA_BATCH:
                        logger.info("Resetting session after batch")
                        downloaded_count = 0
                        self.init_session()
                        sp["app_token"] = self.app_token
                        break
                except Exception:
                    logger.error("Row failed:", exc_info=True)
            else:
                sp["sEcho"] += 1
                sp["iDisplayStart"] += PAGE_SIZE

    def _handle_row(self, row, idx: int, frm: str, to: str) -> None:
        html = row[1]
        soup = BeautifulSoup(html, "html.parser")
        btn = soup.find("button", onclick=True)
        if not btn:
            return

        frag_m = re.search(r"open_pdf\('.*?','.*?','(.*?)'\)", btn["onclick"])
        frag = frag_m.group(1).split("#")[0] if frag_m else None
        if not frag:
            return

        # ✅ Skip if already downloaded
        if self.already_downloaded(frag, frm, to):
            logger.info(f"⏩ Skipping already downloaded case: {frag}")
            return

        pdf_path = self.get_pdf_path(frag, frm, to)
        meta_path = self.get_meta_path(frag, frm, to)
        fresh = False

        # 1) Download PDF
        lp = self.default_pdf_payload()
        lp.update({"path": frag, "val": idx, "app_token": self.app_token or ""})
        r2 = self.request_api("POST", PDF_LINK_URL, lp)
        j2 = r2.json()
        if "outputfile" in j2:
            url = ROOT_URL + j2["outputfile"]
            pdf_resp = self.session.get(url, verify=False, timeout=60)
            content = pdf_resp.content
            if content.lstrip().startswith(b"%PDF"):
                pdf_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                pdf_path.write_bytes(content)
                pdf_path.chmod(0o644)
                fresh = True
            else:
                logger.error(f"Skipped corrupt HTML in place of PDF: {frag}")
        else:
            logger.error("No outputfile in PDF-link response")

        # 2) Build metadata dict
        meta = self._parse_metadata(html)
        meta.update({
            "court_code": self.code,
            "court": self.name,
            "pdf_link": frag,
            "downloaded": fresh,
            "from_date": frm,
            "to_date": to
        })

        # 3) Save metadata locally
        save_json(meta_path, meta)

        # 4) Upload PDF → get PDF URL
        slug = slugify(self.name)
        year = frm[:4]
        gcs_pdf_key = f"pdf/highcourt/{slug}/{year}/{pdf_path.name}"
        gcs_meta_key = f"metadata/highcourt/{slug}/{year}/{meta_path.name}"

        try:
            pdf_url = upload_to_gcs(str(pdf_path), gcs_pdf_key)
            meta["pdfpathgcs"] = gcs_pdf_key
            meta["pdfurl"] = pdf_url
            save_json(meta_path, meta)
            upload_to_gcs(str(meta_path), gcs_meta_key)
            logger.info(f"Uploaded PDF+meta to GCS: {gcs_pdf_key}, {gcs_meta_key}")
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")

# ─── Main Entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Download e-Court judgments and push to GCS")
    p.add_argument("--court_codes", required=True,
                   help="Comma-separated codes, e.g. '9~13,27~1,19~16,18~6'")
    p.add_argument("--start_date", type=str, default=None,
                   help="YYYY-MM-DD start (falls back to track.json)")
    p.add_argument("--end_date", type=str, default=None,
                   help="YYYY-MM-DD end (optional)")
    p.add_argument("--day_step", type=int, default=1,
                   help="Days per batch")
    p.add_argument("--max_workers", type=int, default=4,
                   help="Parallel threads")
    args = p.parse_args()

    codes = [c.strip() for c in args.court_codes.split(",")]
    run(codes, args.start_date, args.end_date, args.day_step, args.max_workers)
