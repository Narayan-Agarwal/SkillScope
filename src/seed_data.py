"""
Data pipeline for SkillScope — downloads, cleans, and seeds the SQLite database.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    filename="data/pipeline.log",
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROLE_MAPPING: dict[str, str] = {
    # SDE
    "software engineer": "SDE",
    "software developer": "SDE",
    "sde": "SDE",
    "sde-1": "SDE",
    "sde-2": "SDE",
    "senior sde": "SDE",
    # Frontend Developer
    "frontend engineer": "Frontend Developer",
    "ui developer": "Frontend Developer",
    "react developer": "Frontend Developer",
    "frontend developer": "Frontend Developer",
    # Backend Developer
    "backend engineer": "Backend Developer",
    "backend developer": "Backend Developer",
    "api developer": "Backend Developer",
    "node.js developer": "Backend Developer",
    # Full Stack Developer
    "full stack engineer": "Full Stack Developer",
    "full stack developer": "Full Stack Developer",
    "mean stack developer": "Full Stack Developer",
    "mern stack developer": "Full Stack Developer",
    # Data Analyst
    "data analyst": "Data Analyst",
    "bi analyst": "Data Analyst",
    "senior data analyst": "Data Analyst",
    # Data Scientist
    "data scientist": "Data Scientist",
    "senior data scientist": "Data Scientist",
    "applied scientist": "Data Scientist",
    # ML Engineer
    "machine learning engineer": "ML Engineer",
    "ml engineer": "ML Engineer",
    "ai/ml engineer": "ML Engineer",
    "mlops engineer": "ML Engineer",
    # DevOps Engineer
    "devops engineer": "DevOps Engineer",
    "site reliability engineer": "DevOps Engineer",
    "sre": "DevOps Engineer",
    "platform engineer": "DevOps Engineer",
    # Cloud Engineer
    "cloud engineer": "Cloud Engineer",
    "cloud architect": "Cloud Engineer",
    "aws engineer": "Cloud Engineer",
    "azure engineer": "Cloud Engineer",
    # Business Analyst
    "business analyst": "Business Analyst",
    "functional analyst": "Business Analyst",
    # Product Manager
    "product manager": "Product Manager",
    "pm": "Product Manager",
    "product owner": "Product Manager",
    # QA Engineer
    "qa engineer": "QA Engineer",
    "quality assurance engineer": "QA Engineer",
    "test engineer": "QA Engineer",
    "sdet": "QA Engineer",
    # Cybersecurity Analyst
    "cybersecurity analyst": "Cybersecurity Analyst",
    "security analyst": "Cybersecurity Analyst",
    "soc analyst": "Cybersecurity Analyst",
    # System Administrator
    "system administrator": "System Administrator",
    "sysadmin": "System Administrator",
    "it administrator": "System Administrator",
    # Game Developer
    "game developer": "Game Developer",
    "unity developer": "Game Developer",
    "unreal developer": "Game Developer",
}

VALID_ROLES: set[str] = set(ROLE_MAPPING.values()) | {"Other"}

COMPANY_TIER_MAP: dict[str, str] = {
    # Product
    "Google": "Product",
    "Microsoft": "Product",
    "Amazon": "Product",
    "Meta": "Product",
    "Apple": "Product",
    "Adobe": "Product",
    "Salesforce": "Product",
    "Oracle": "Product",
    "IBM": "Product",
    "Nvidia": "Product",
    "Cisco": "Product",
    # Indian IT
    "TCS": "Indian IT",
    "Infosys": "Indian IT",
    "Wipro": "Indian IT",
    "HCL Technologies": "Indian IT",
    "Cognizant": "Indian IT",
    "Accenture": "Indian IT",
    "Capgemini": "Indian IT",
    "Tech Mahindra": "Indian IT",
    "Mphasis": "Indian IT",
    "Hexaware": "Indian IT",
    "LTIMindtree": "Indian IT",
    "Persistent Systems": "Indian IT",
    "Cyient": "Indian IT",
    "Birlasoft": "Indian IT",
    "Coforge": "Indian IT",
    "Zensar Technologies": "Indian IT",
    "Mastech Digital": "Indian IT",
    "NIIT Technologies": "Indian IT",
    # Startup
    "Razorpay": "Startup",
    "CRED": "Startup",
    "Swiggy": "Startup",
    "Zomato": "Startup",
    "Paytm": "Startup",
    "PhonePe": "Startup",
    "Meesho": "Startup",
    "Zepto": "Startup",
    "Blinkit": "Startup",
    "Groww": "Startup",
    "Zerodha": "Startup",
    "Navi": "Startup",
    "Slice": "Startup",
    "Urban Company": "Startup",
    "OYO": "Startup",
    "MakeMyTrip": "Startup",
    "Ola": "Startup",
    "Rapido": "Startup",
    "Porter": "Startup",
    # EdTech
    "BYJU'S": "EdTech",
    "Unacademy": "EdTech",
    "Vedantu": "EdTech",
    "upGrad": "EdTech",
    "Scaler": "EdTech",
    "Physics Wallah": "EdTech",
    "Simplilearn": "EdTech",
    "Great Learning": "EdTech",
    "Coding Ninjas": "EdTech",
    "InterviewBit": "EdTech",
    "Coursera India": "EdTech",
    "Toppr": "EdTech",
    "Classplus": "EdTech",
    "Teachmint": "EdTech",
    # Esports
    "Nodwin Gaming": "Esports",
    "WinZO": "Esports",
    "MPL": "Esports",
    "Dream11": "Esports",
    "Games24x7": "Esports",
    "Nazara Technologies": "Esports",
    "Rooter": "Esports",
    "Krafton India": "Esports",
    "nCore Games": "Esports",
    "Ubisoft India": "Esports",
    "EA India": "Esports",
    # Consulting
    "Deloitte": "Consulting",
    "EY": "Consulting",
    "KPMG": "Consulting",
    "McKinsey": "Consulting",
    "BCG": "Consulting",
    "Bain & Company": "Consulting",
    "PwC": "Consulting",
    "Gartner": "Consulting",
    "Mu Sigma": "Consulting",
    "Tiger Analytics": "Consulting",
    "Fractal Analytics": "Consulting",
    "LatentView Analytics": "Consulting",
    "Bridgei2i": "Consulting",
    "Absolutdata": "Consulting",
    "Indegene": "Consulting",
    "ZS Associates": "Consulting",
    "Kantar": "Consulting",
    "Nielsen": "Consulting",
}

VALID_TIERS: set[str] = {"Product", "Indian IT", "Startup", "EdTech", "Esports", "Consulting", "Other"}

# Company name variant normalization
COMPANY_NAME_VARIANTS: dict[str, str] = {
    "Google LLC": "Google",
    "Amazon.com": "Amazon",
    "Meta Platforms": "Meta",
    "Apple Inc": "Apple",
}

INDUSTRY_STANDARD_FALLBACK: dict[str, Any] = {
    "Product": {
        "SDE": [
            ("Python", "Programming"),
            ("Java", "Programming"),
            ("System Design", "Tools & Practices"),
            ("AWS", "Cloud & DevOps"),
            ("Docker", "Cloud & DevOps"),
        ],
        "Data Scientist": [
            ("Python", "Programming"),
            ("TensorFlow", "Data & ML"),
            ("SQL", "Data & ML"),
            ("Pandas", "Data & ML"),
        ],
    },
    "Indian IT": {
        "SDE": [
            ("Java", "Programming"),
            ("SQL", "Data & ML"),
            ("Agile", "Tools & Practices"),
            ("Git", "Tools & Practices"),
        ],
    },
    "Startup": {
        "SDE": [
            ("Python", "Programming"),
            ("React", "Web"),
            ("Node.js", "Web"),
            ("PostgreSQL", "Database"),
        ],
    },
    "EdTech": {
        "SDE": [
            ("Python", "Programming"),
            ("Django", "Web"),
            ("PostgreSQL", "Database"),
            ("AWS", "Cloud & DevOps"),
        ],
    },
    "Esports": {
        "Game Developer": [
            ("Unity", "Domain Specific"),
            ("C#", "Programming"),
            ("Unreal Engine", "Domain Specific"),
            ("C++", "Programming"),
        ],
    },
    "Consulting": {
        "Data Analyst": [
            ("SQL", "Data & ML"),
            ("Excel", "Data & ML"),
            ("Tableau", "Data & ML"),
            ("Python", "Programming"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper functions (exported for testing)
# ---------------------------------------------------------------------------

def normalize_role(title: str) -> str:
    """Map a raw job title to one of the 15 Normalized_Roles or 'Other'."""
    if not title or not isinstance(title, str):
        return "Other"
    return ROLE_MAPPING.get(title.strip().lower(), "Other")


def get_tier(company_name: str) -> str:
    """Map a company name to one of the 6 Tiers or 'Other'."""
    if not company_name or not isinstance(company_name, str):
        return "Other"
    return COMPANY_TIER_MAP.get(company_name.strip(), "Other")


def normalize_text(text: str) -> str:
    """Apply title case normalization to a string."""
    return text.title()


# ---------------------------------------------------------------------------
# Pipeline functions
# ---------------------------------------------------------------------------

def download_kaggle(output_path: str) -> None:
    """Download the LinkedIn job postings dataset from Kaggle.

    Retries up to 3 times with exponential backoff (2^attempt seconds).
    Exits with code 1 on credential failure or exhausted retries.
    """
    load_dotenv()
    token = os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY")

    if not token:
        msg = "Kaggle credential error: KAGGLE_API_TOKEN / KAGGLE_KEY not set in environment."
        logging.error(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)

    os.environ["KAGGLE_API_TOKEN"] = token

    def _attempt_download() -> None:
        # Import kaggle here so the env var is already set
        import kaggle  # noqa: F401 — triggers auth from env
        from kaggle.api.kaggle_api_extended import KaggleApiExtended

        api = KaggleApiExtended()
        api.authenticate()

        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        api.dataset_download_files(
            "arshkon/linkedin-job-postings",
            path=os.path.dirname(output_path) or ".",
            unzip=True,
            quiet=False,
            force=True,
        )

    retries = 3
    for attempt in range(retries):
        try:
            _attempt_download()
            # Find the downloaded CSV
            base_dir = os.path.dirname(output_path) or "."
            csv_candidates = [f for f in os.listdir(base_dir) if f.endswith(".csv")]
            if csv_candidates:
                # Rename/move the first CSV to the expected output_path
                src = os.path.join(base_dir, csv_candidates[0])
                if src != output_path:
                    os.rename(src, output_path)
            df = pd.read_csv(output_path)
            print(f"Kaggle download complete. Rows: {len(df)}")
            return
        except SystemExit:
            raise
        except Exception as exc:
            err_str = str(exc).lower()
            if "401" in err_str or "unauthorized" in err_str or "credential" in err_str or "api key" in err_str:
                msg = f"Kaggle credential error: {exc}"
                logging.error(msg)
                print(msg, file=sys.stderr)
                sys.exit(1)
            if attempt < retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                msg = f"Kaggle download failed after {retries} attempts: {exc}"
                logging.error(msg, exc_info=True)
                print(msg, file=sys.stderr)
                sys.exit(1)


def load_and_clean(csv_path: str) -> pd.DataFrame:
    """Load and clean the raw Kaggle CSV.

    Steps:
    - Normalize column names
    - Apply company name variants
    - Map roles and tiers
    - Drop null/empty title+description rows
    - Deduplicate on (company_name, role_title)
    - Drop rows with fewer than 3 extracted skills
    """
    # Import here to avoid circular issues at module level
    sys.path.insert(0, os.path.dirname(__file__))
    from skill_extractor import extract_skills

    df = pd.read_csv(csv_path)

    # Normalize column names
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    # Identify company name column
    company_col = None
    for candidate in ("company_name", "company"):
        if candidate in df.columns:
            company_col = candidate
            break
    if company_col is None:
        # Use first column that looks like a company
        company_col = df.columns[0]

    # Identify title column
    title_col = None
    for candidate in ("title", "job_title"):
        if candidate in df.columns:
            title_col = candidate
            break

    # Identify description column
    desc_col = None
    for candidate in ("description", "job_description"):
        if candidate in df.columns:
            desc_col = candidate
            break

    # Rename to standard names
    rename_map: dict[str, str] = {}
    if company_col and company_col != "company_name":
        rename_map[company_col] = "company_name"
    if title_col and title_col != "role_title":
        rename_map[title_col] = "role_title"
    if desc_col and desc_col != "description":
        rename_map[desc_col] = "description"
    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure columns exist
    if "company_name" not in df.columns:
        df["company_name"] = ""
    if "role_title" not in df.columns:
        df["role_title"] = ""
    if "description" not in df.columns:
        df["description"] = ""

    # Apply company name variants
    df["company_name"] = df["company_name"].astype(str).replace(COMPANY_NAME_VARIANTS)

    # Drop rows where both title and description are null/empty
    title_empty = df["role_title"].isna() | (df["role_title"].astype(str).str.strip() == "")
    desc_empty = df["description"].isna() | (df["description"].astype(str).str.strip() == "")
    df = df[~(title_empty & desc_empty)].copy()

    # Map role titles to normalized roles
    df["role_title"] = df["role_title"].astype(str).apply(normalize_role)

    # Map companies to tiers
    df["tier"] = df["company_name"].apply(get_tier)

    # Normalize company names and role titles to title case
    df["company_name"] = df["company_name"].apply(normalize_text)
    df["role_title"] = df["role_title"].apply(normalize_text)

    # Deduplicate on (company_name, role_title) — keep first
    df = df.drop_duplicates(subset=["company_name", "role_title"], keep="first").copy()

    # Drop rows with fewer than 3 extracted skills
    def _skill_count(row: pd.Series) -> int:
        text = " ".join([
            str(row.get("role_title", "")),
            str(row.get("description", "")),
        ])
        return len(extract_skills(text))

    df["_skill_count"] = df.apply(_skill_count, axis=1)
    df = df[df["_skill_count"] >= 3].drop(columns=["_skill_count"]).copy()

    company_count = df["company_name"].nunique()
    print(f"Cleaned rows: {len(df)} across {company_count} companies.")
    return df


def fetch_adzuna(roles: list[str], pages: int = 3) -> list[dict]:
    """Fetch job postings from the Adzuna API for the given roles.

    Handles non-2xx responses (logs and returns empty list for that role)
    and 429 rate limiting (pauses 60 seconds, retries once).
    """
    load_dotenv()
    app_id = os.environ.get("ADZUNA_APP_ID", "")
    app_key = os.environ.get("ADZUNA_APP_KEY", "")

    results: list[dict] = []
    companies_seen: set[str] = set()

    for role in roles:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/in/search/1"
            f"?app_id={app_id}&app_key={app_key}&what={requests.utils.quote(role)}&results_per_page=10"
        )
        for attempt in range(2):
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 429:
                    if attempt == 0:
                        time.sleep(60)
                        continue
                    else:
                        msg = f"Adzuna 429 rate limit for role '{role}' after retry."
                        logging.error(msg)
                        print(msg, file=sys.stderr)
                        break
                if not resp.ok:
                    msg = f"Adzuna HTTP {resp.status_code} for role '{role}'."
                    logging.error(msg)
                    print(msg, file=sys.stderr)
                    break
                data = resp.json()
                for job in data.get("results", []):
                    title = job.get("title", "")
                    description = job.get("description", "")
                    company = job.get("company", {}).get("display_name", "") if isinstance(job.get("company"), dict) else str(job.get("company", ""))
                    results.append({"title": title, "description": description, "company": company})
                    if company:
                        companies_seen.add(company)
                break
            except Exception as exc:
                msg = f"Adzuna request error for role '{role}': {exc}"
                logging.error(msg)
                print(msg, file=sys.stderr)
                break

    print(f"Adzuna gap fill complete. Companies now with data: {len(companies_seen)} / 91")
    return results


def run_pipeline() -> None:
    """Orchestrate the full data pipeline: download → clean → Adzuna → DB writes."""
    try:
        _run_pipeline_inner()
    except SystemExit:
        raise
    except Exception:
        tb = traceback.format_exc()
        logging.error("Unhandled pipeline exception:\n%s", tb)
        print(f"Pipeline failed. See data/pipeline.log for details.", file=sys.stderr)
        sys.exit(1)


def _run_pipeline_inner() -> None:
    """Inner pipeline logic (separated so run_pipeline can catch exceptions)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from db import create_schema, get_connection, insert_job_role, insert_role_skill, upsert_company, upsert_skill_frequency
    from skill_extractor import extract_skills

    kaggle_path = "data/kaggle_raw.csv"

    # Step 1: Download Kaggle data
    download_kaggle(kaggle_path)

    # Step 2: Clean and normalize
    df = load_and_clean(kaggle_path)

    # Step 3: Fetch Adzuna gap-fill data
    roles_list = list(ROLE_MAPPING.values())
    adzuna_records = fetch_adzuna(roles_list)

    # Step 4: Connect to DB and create schema
    conn = get_connection()
    create_schema(conn)

    company_count = 0
    role_count = 0
    skill_record_count = 0
    unique_skills: set[str] = set()

    # Step 5: Write Kaggle records
    for _, row in df.iterrows():
        company_name = str(row.get("company_name", "Unknown"))
        role_title = str(row.get("role_title", "Other"))
        tier = str(row.get("tier", "Other"))
        description = str(row.get("description", ""))

        company_id = upsert_company(conn, company_name, tier, None)
        company_count += 1

        role_id = insert_job_role(conn, company_id, role_title, None)
        role_count += 1

        skills = extract_skills(f"{role_title} {description}")
        for skill_name, skill_category in skills:
            insert_role_skill(conn, role_id, skill_name, skill_category, "kaggle")
            upsert_skill_frequency(conn, skill_name, skill_category)
            skill_record_count += 1
            unique_skills.add(skill_name)

    # Step 6: Write Adzuna records
    for record in adzuna_records:
        company_name = normalize_text(str(record.get("company", "Unknown")))
        raw_title = str(record.get("title", ""))
        role_title = normalize_text(normalize_role(raw_title))
        description = str(record.get("description", ""))
        tier = get_tier(company_name)

        company_id = upsert_company(conn, company_name, tier, None)
        role_id = insert_job_role(conn, company_id, role_title, None)
        role_count += 1

        skills = extract_skills(f"{role_title} {description}")
        for skill_name, skill_category in skills:
            insert_role_skill(conn, role_id, skill_name, skill_category, "adzuna")
            upsert_skill_frequency(conn, skill_name, skill_category)
            skill_record_count += 1
            unique_skills.add(skill_name)

    # Step 7: Industry standard fallback for companies with fewer than 3 roles
    company_role_counts: dict[str, int] = {}
    for _, row in df.iterrows():
        cname = str(row.get("company_name", ""))
        company_role_counts[cname] = company_role_counts.get(cname, 0) + 1

    for tier_name, role_skills_map in INDUSTRY_STANDARD_FALLBACK.items():
        # Find companies in this tier with fewer than 3 roles
        for company_name, tier in COMPANY_TIER_MAP.items():
            if tier != tier_name:
                continue
            normalized_name = normalize_text(company_name)
            if company_role_counts.get(normalized_name, 0) >= 3:
                continue
            for role_title, skills in role_skills_map.items():
                company_id = upsert_company(conn, normalized_name, tier_name, None)
                role_id = insert_job_role(conn, company_id, role_title, None)
                role_count += 1
                for skill_name, skill_category in skills:
                    insert_role_skill(conn, role_id, skill_name, skill_category, "kaggle")
                    upsert_skill_frequency(conn, skill_name, skill_category)
                    skill_record_count += 1
                    unique_skills.add(skill_name)

    conn.close()

    print(
        f"Database write complete. "
        f"Companies: {company_count} | "
        f"Roles: {role_count} | "
        f"Skill records: {skill_record_count} | "
        f"Unique skills tracked: {len(unique_skills)}"
    )


if __name__ == "__main__":
    run_pipeline()
