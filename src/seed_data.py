"""
Data pipeline for SkillScope.
Strategy: Adzuna API first (company + role queries), then guaranteed fallback for all 91 companies.
Kaggle download is commented out — not used for seeding.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    filename="data/pipeline.log",
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s",
)

# ---------------------------------------------------------------------------
# KAGGLE DOWNLOAD — commented out, not used for seeding
# ---------------------------------------------------------------------------
# def download_kaggle(output_path: str) -> None:
#     """Previously used to download LinkedIn job postings from Kaggle.
#     Disabled: dataset is 159MB and takes too long for initial seeding.
#     Use Adzuna API + fallback instead."""
#     import kaggle
#     kaggle.api.dataset_download_files(
#         "arshkon/linkedin-job-postings",
#         path=os.path.dirname(output_path) or ".",
#         unzip=True,
#     )
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROLE_MAPPING: dict[str, str] = {
    "software engineer": "SDE",
    "software developer": "SDE",
    "sde": "SDE",
    "frontend engineer": "Frontend Developer",
    "frontend developer": "Frontend Developer",
    "react developer": "Frontend Developer",
    "ui developer": "Frontend Developer",
    "backend engineer": "Backend Developer",
    "backend developer": "Backend Developer",
    "node.js developer": "Backend Developer",
    "full stack engineer": "Full Stack Developer",
    "full stack developer": "Full Stack Developer",
    "data analyst": "Data Analyst",
    "bi analyst": "Data Analyst",
    "data scientist": "Data Scientist",
    "applied scientist": "Data Scientist",
    "machine learning engineer": "ML Engineer",
    "ml engineer": "ML Engineer",
    "mlops engineer": "ML Engineer",
    "devops engineer": "DevOps Engineer",
    "site reliability engineer": "DevOps Engineer",
    "sre": "DevOps Engineer",
    "cloud engineer": "Cloud Engineer",
    "cloud architect": "Cloud Engineer",
    "business analyst": "Business Analyst",
    "product manager": "Product Manager",
    "product owner": "Product Manager",
    "qa engineer": "QA Engineer",
    "test engineer": "QA Engineer",
    "sdet": "QA Engineer",
    "cybersecurity analyst": "Cybersecurity Analyst",
    "security analyst": "Cybersecurity Analyst",
    "system administrator": "System Administrator",
    "sysadmin": "System Administrator",
    "game developer": "Game Developer",
    "unity developer": "Game Developer",
}

NORMALIZED_ROLES = [
    "SDE", "Frontend Developer", "Backend Developer", "Full Stack Developer",
    "Data Analyst", "Data Scientist", "ML Engineer", "DevOps Engineer",
    "Cloud Engineer", "Business Analyst", "Product Manager", "QA Engineer",
    "Cybersecurity Analyst", "System Administrator", "Game Developer",
]

COMPANY_TIER_MAP: dict[str, str] = {
    "Google": "Product", "Microsoft": "Product", "Amazon": "Product",
    "Meta": "Product", "Apple": "Product", "Adobe": "Product",
    "Salesforce": "Product", "Oracle": "Product", "IBM": "Product",
    "Nvidia": "Product", "Cisco": "Product",
    "TCS": "Indian IT", "Infosys": "Indian IT", "Wipro": "Indian IT",
    "HCL Technologies": "Indian IT", "Cognizant": "Indian IT",
    "Accenture": "Indian IT", "Capgemini": "Indian IT",
    "Tech Mahindra": "Indian IT", "Mphasis": "Indian IT",
    "Hexaware": "Indian IT", "LTIMindtree": "Indian IT",
    "Persistent Systems": "Indian IT", "Cyient": "Indian IT",
    "Birlasoft": "Indian IT", "Coforge": "Indian IT",
    "Zensar Technologies": "Indian IT", "Mastech Digital": "Indian IT",
    "NIIT Technologies": "Indian IT",
    "Razorpay": "Startup", "CRED": "Startup", "Swiggy": "Startup",
    "Zomato": "Startup", "Paytm": "Startup", "PhonePe": "Startup",
    "Meesho": "Startup", "Zepto": "Startup", "Blinkit": "Startup",
    "Groww": "Startup", "Zerodha": "Startup", "Navi": "Startup",
    "Slice": "Startup", "Urban Company": "Startup", "OYO": "Startup",
    "MakeMyTrip": "Startup", "Ola": "Startup", "Rapido": "Startup",
    "Porter": "Startup",
    "BYJU'S": "EdTech", "Unacademy": "EdTech", "Vedantu": "EdTech",
    "upGrad": "EdTech", "Scaler": "EdTech", "Physics Wallah": "EdTech",
    "Simplilearn": "EdTech", "Great Learning": "EdTech",
    "Coding Ninjas": "EdTech", "InterviewBit": "EdTech",
    "Coursera India": "EdTech", "Toppr": "EdTech",
    "Classplus": "EdTech", "Teachmint": "EdTech",
    "Nodwin Gaming": "Esports", "WinZO": "Esports", "MPL": "Esports",
    "Dream11": "Esports", "Games24x7": "Esports",
    "Nazara Technologies": "Esports", "Rooter": "Esports",
    "Krafton India": "Esports", "nCore Games": "Esports",
    "Ubisoft India": "Esports", "EA India": "Esports",
    "Deloitte": "Consulting", "EY": "Consulting", "KPMG": "Consulting",
    "McKinsey": "Consulting", "BCG": "Consulting",
    "Bain & Company": "Consulting", "PwC": "Consulting",
    "Gartner": "Consulting", "Mu Sigma": "Consulting",
    "Tiger Analytics": "Consulting", "Fractal Analytics": "Consulting",
    "LatentView Analytics": "Consulting", "Bridgei2i": "Consulting",
    "Absolutdata": "Consulting", "Indegene": "Consulting",
    "ZS Associates": "Consulting", "Kantar": "Consulting",
    "Nielsen": "Consulting",
}

# ---------------------------------------------------------------------------
# Comprehensive fallback skill data — guaranteed, no API needed
# ---------------------------------------------------------------------------

FALLBACK_SKILLS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "Product": {
        "SDE": [
            ("Python", "Programming"), ("Java", "Programming"), ("Go", "Programming"),
            ("System Design", "Tools_and_Practices"), ("AWS", "Cloud_and_DevOps"),
            ("Docker", "Cloud_and_DevOps"), ("Kubernetes", "Cloud_and_DevOps"),
            ("React", "Web"), ("PostgreSQL", "Database"), ("Redis", "Database"),
        ],
        "Data Scientist": [
            ("Python", "Programming"), ("TensorFlow", "Data_and_ML"),
            ("PyTorch", "Data_and_ML"), ("SQL", "Database"),
            ("Pandas", "Data_and_ML"), ("Scikit-learn", "Data_and_ML"),
            ("Spark", "Data_and_ML"), ("Tableau", "Tools_and_Practices"),
            ("Statistics", "Data_and_ML"), ("Machine Learning", "Data_and_ML"),
        ],
        "ML Engineer": [
            ("Python", "Programming"), ("TensorFlow", "Data_and_ML"),
            ("PyTorch", "Data_and_ML"), ("MLflow", "Tools_and_Practices"),
            ("Docker", "Cloud_and_DevOps"), ("Kubernetes", "Cloud_and_DevOps"),
            ("AWS SageMaker", "Cloud_and_DevOps"), ("Spark", "Data_and_ML"),
            ("Feature Engineering", "Data_and_ML"), ("Model Deployment", "Data_and_ML"),
        ],
        "DevOps Engineer": [
            ("Docker", "Cloud_and_DevOps"), ("Kubernetes", "Cloud_and_DevOps"),
            ("Terraform", "Cloud_and_DevOps"), ("AWS", "Cloud_and_DevOps"),
            ("CI/CD", "Tools_and_Practices"), ("Jenkins", "Tools_and_Practices"),
            ("Linux", "Tools_and_Practices"), ("Python", "Programming"),
            ("Prometheus", "Tools_and_Practices"), ("Grafana", "Tools_and_Practices"),
        ],
        "Frontend Developer": [
            ("React", "Web"), ("TypeScript", "Programming"), ("JavaScript", "Programming"),
            ("CSS", "Web"), ("HTML", "Web"), ("Redux", "Web"),
            ("GraphQL", "Web"), ("Jest", "Tools_and_Practices"),
            ("Webpack", "Tools_and_Practices"), ("Figma", "Tools_and_Practices"),
        ],
    },
    "Indian IT": {
        "SDE": [
            ("Java", "Programming"), ("Python", "Programming"), ("SQL", "Database"),
            ("Spring Boot", "Web"), ("Hibernate", "Database"),
            ("Agile", "Tools_and_Practices"), ("Git", "Tools_and_Practices"),
            ("REST API", "Web"), ("MySQL", "Database"), ("Maven", "Tools_and_Practices"),
        ],
        "Data Analyst": [
            ("SQL", "Database"), ("Excel", "Tools_and_Practices"),
            ("Python", "Programming"), ("Tableau", "Tools_and_Practices"),
            ("Power BI", "Tools_and_Practices"), ("Pandas", "Data_and_ML"),
            ("Statistics", "Data_and_ML"), ("Data Visualization", "Data_and_ML"),
            ("ETL", "Data_and_ML"), ("JIRA", "Tools_and_Practices"),
        ],
        "Business Analyst": [
            ("SQL", "Database"), ("Excel", "Tools_and_Practices"),
            ("JIRA", "Tools_and_Practices"), ("Agile", "Tools_and_Practices"),
            ("Requirements Gathering", "Domain_Specific"),
            ("Stakeholder Management", "Soft_Skills"),
            ("Power BI", "Tools_and_Practices"), ("Visio", "Tools_and_Practices"),
            ("UAT", "Tools_and_Practices"), ("Documentation", "Soft_Skills"),
        ],
        "QA Engineer": [
            ("Selenium", "Tools_and_Practices"), ("Java", "Programming"),
            ("TestNG", "Tools_and_Practices"), ("JIRA", "Tools_and_Practices"),
            ("SQL", "Database"), ("Postman", "Tools_and_Practices"),
            ("Agile", "Tools_and_Practices"), ("API Testing", "Tools_and_Practices"),
            ("Git", "Tools_and_Practices"), ("Manual Testing", "Tools_and_Practices"),
        ],
        "DevOps Engineer": [
            ("Jenkins", "Tools_and_Practices"), ("Docker", "Cloud_and_DevOps"),
            ("Linux", "Tools_and_Practices"), ("AWS", "Cloud_and_DevOps"),
            ("Ansible", "Cloud_and_DevOps"), ("Git", "Tools_and_Practices"),
            ("Shell Scripting", "Programming"), ("Kubernetes", "Cloud_and_DevOps"),
            ("CI/CD", "Tools_and_Practices"), ("Terraform", "Cloud_and_DevOps"),
        ],
    },
    "Startup": {
        "SDE": [
            ("Python", "Programming"), ("React", "Web"), ("Node.js", "Web"),
            ("PostgreSQL", "Database"), ("Docker", "Cloud_and_DevOps"),
            ("AWS", "Cloud_and_DevOps"), ("TypeScript", "Programming"),
            ("Redis", "Database"), ("GraphQL", "Web"), ("Git", "Tools_and_Practices"),
        ],
        "Full Stack Developer": [
            ("React", "Web"), ("Node.js", "Web"), ("Python", "Programming"),
            ("MongoDB", "Database"), ("PostgreSQL", "Database"),
            ("Docker", "Cloud_and_DevOps"), ("AWS", "Cloud_and_DevOps"),
            ("TypeScript", "Programming"), ("REST API", "Web"), ("Git", "Tools_and_Practices"),
        ],
        "Data Scientist": [
            ("Python", "Programming"), ("Machine Learning", "Data_and_ML"),
            ("SQL", "Database"), ("Pandas", "Data_and_ML"),
            ("Scikit-learn", "Data_and_ML"), ("TensorFlow", "Data_and_ML"),
            ("Statistics", "Data_and_ML"), ("Data Visualization", "Data_and_ML"),
            ("Spark", "Data_and_ML"), ("Airflow", "Tools_and_Practices"),
        ],
        "Product Manager": [
            ("Product Roadmap", "Domain_Specific"), ("Agile", "Tools_and_Practices"),
            ("JIRA", "Tools_and_Practices"), ("SQL", "Database"),
            ("A/B Testing", "Data_and_ML"), ("User Research", "Domain_Specific"),
            ("Figma", "Tools_and_Practices"), ("Analytics", "Data_and_ML"),
            ("Stakeholder Management", "Soft_Skills"), ("OKRs", "Domain_Specific"),
        ],
        "DevOps Engineer": [
            ("Docker", "Cloud_and_DevOps"), ("Kubernetes", "Cloud_and_DevOps"),
            ("AWS", "Cloud_and_DevOps"), ("Terraform", "Cloud_and_DevOps"),
            ("CI/CD", "Tools_and_Practices"), ("Python", "Programming"),
            ("Linux", "Tools_and_Practices"), ("Prometheus", "Tools_and_Practices"),
            ("Git", "Tools_and_Practices"), ("Helm", "Cloud_and_DevOps"),
        ],
    },
    "EdTech": {
        "SDE": [
            ("Python", "Programming"), ("Django", "Web"),
            ("PostgreSQL", "Database"), ("AWS", "Cloud_and_DevOps"),
            ("React", "Web"), ("Redis", "Database"),
            ("Docker", "Cloud_and_DevOps"), ("REST API", "Web"),
            ("Git", "Tools_and_Practices"), ("Celery", "Tools_and_Practices"),
        ],
        "Data Scientist": [
            ("Python", "Programming"), ("Machine Learning", "Data_and_ML"),
            ("SQL", "Database"), ("Pandas", "Data_and_ML"),
            ("NLP", "AI_and_GenAI"), ("Recommendation Systems", "Data_and_ML"),
            ("Scikit-learn", "Data_and_ML"), ("Statistics", "Data_and_ML"),
            ("A/B Testing", "Data_and_ML"), ("TensorFlow", "Data_and_ML"),
        ],
        "Product Manager": [
            ("Product Roadmap", "Domain_Specific"), ("Agile", "Tools_and_Practices"),
            ("SQL", "Database"), ("User Research", "Domain_Specific"),
            ("A/B Testing", "Data_and_ML"), ("JIRA", "Tools_and_Practices"),
            ("Analytics", "Data_and_ML"), ("Figma", "Tools_and_Practices"),
            ("Communication", "Soft_Skills"), ("OKRs", "Domain_Specific"),
        ],
        "Frontend Developer": [
            ("React", "Web"), ("JavaScript", "Programming"),
            ("TypeScript", "Programming"), ("CSS", "Web"),
            ("HTML", "Web"), ("Redux", "Web"),
            ("Jest", "Tools_and_Practices"), ("Webpack", "Tools_and_Practices"),
            ("Git", "Tools_and_Practices"), ("Figma", "Tools_and_Practices"),
        ],
        "ML Engineer": [
            ("Python", "Programming"), ("TensorFlow", "Data_and_ML"),
            ("NLP", "AI_and_GenAI"), ("Recommendation Systems", "Data_and_ML"),
            ("Docker", "Cloud_and_DevOps"), ("AWS", "Cloud_and_DevOps"),
            ("Scikit-learn", "Data_and_ML"), ("Pandas", "Data_and_ML"),
            ("MLflow", "Tools_and_Practices"), ("Spark", "Data_and_ML"),
        ],
    },
    "Esports": {
        "Game Developer": [
            ("Unity", "Domain_Specific"), ("C#", "Programming"),
            ("Unreal Engine", "Domain_Specific"), ("C++", "Programming"),
            ("Game Physics", "Domain_Specific"), ("3D Modeling", "Domain_Specific"),
            ("Multiplayer Networking", "Domain_Specific"), ("Git", "Tools_and_Practices"),
            ("Shader Programming", "Domain_Specific"), ("Performance Optimization", "Tools_and_Practices"),
        ],
        "SDE": [
            ("Python", "Programming"), ("Node.js", "Web"),
            ("PostgreSQL", "Database"), ("Redis", "Database"),
            ("AWS", "Cloud_and_DevOps"), ("Docker", "Cloud_and_DevOps"),
            ("WebSockets", "Web"), ("REST API", "Web"),
            ("Git", "Tools_and_Practices"), ("Microservices", "Cloud_and_DevOps"),
        ],
        "Data Analyst": [
            ("SQL", "Database"), ("Python", "Programming"),
            ("Tableau", "Tools_and_Practices"), ("Excel", "Tools_and_Practices"),
            ("Game Analytics", "Domain_Specific"), ("Pandas", "Data_and_ML"),
            ("Statistics", "Data_and_ML"), ("Power BI", "Tools_and_Practices"),
            ("Data Visualization", "Data_and_ML"), ("A/B Testing", "Data_and_ML"),
        ],
        "Product Manager": [
            ("Product Roadmap", "Domain_Specific"), ("Agile", "Tools_and_Practices"),
            ("Game Design", "Domain_Specific"), ("User Research", "Domain_Specific"),
            ("SQL", "Database"), ("Analytics", "Data_and_ML"),
            ("JIRA", "Tools_and_Practices"), ("Monetization", "Domain_Specific"),
            ("Communication", "Soft_Skills"), ("OKRs", "Domain_Specific"),
        ],
        "DevOps Engineer": [
            ("Docker", "Cloud_and_DevOps"), ("Kubernetes", "Cloud_and_DevOps"),
            ("AWS", "Cloud_and_DevOps"), ("CI/CD", "Tools_and_Practices"),
            ("Linux", "Tools_and_Practices"), ("Python", "Programming"),
            ("Terraform", "Cloud_and_DevOps"), ("Prometheus", "Tools_and_Practices"),
            ("Git", "Tools_and_Practices"), ("Grafana", "Tools_and_Practices"),
        ],
    },
    "Consulting": {
        "Data Analyst": [
            ("SQL", "Database"), ("Excel", "Tools_and_Practices"),
            ("Tableau", "Tools_and_Practices"), ("Python", "Programming"),
            ("Power BI", "Tools_and_Practices"), ("Statistics", "Data_and_ML"),
            ("Data Visualization", "Data_and_ML"), ("Pandas", "Data_and_ML"),
            ("Communication", "Soft_Skills"), ("Stakeholder Management", "Soft_Skills"),
        ],
        "Data Scientist": [
            ("Python", "Programming"), ("Machine Learning", "Data_and_ML"),
            ("SQL", "Database"), ("R", "Programming"),
            ("Statistics", "Data_and_ML"), ("Tableau", "Tools_and_Practices"),
            ("Scikit-learn", "Data_and_ML"), ("Pandas", "Data_and_ML"),
            ("Communication", "Soft_Skills"), ("Data Visualization", "Data_and_ML"),
        ],
        "Business Analyst": [
            ("SQL", "Database"), ("Excel", "Tools_and_Practices"),
            ("Power BI", "Tools_and_Practices"), ("Tableau", "Tools_and_Practices"),
            ("Requirements Gathering", "Domain_Specific"), ("Agile", "Tools_and_Practices"),
            ("JIRA", "Tools_and_Practices"), ("Stakeholder Management", "Soft_Skills"),
            ("Documentation", "Soft_Skills"), ("Process Mapping", "Domain_Specific"),
        ],
        "ML Engineer": [
            ("Python", "Programming"), ("TensorFlow", "Data_and_ML"),
            ("Scikit-learn", "Data_and_ML"), ("SQL", "Database"),
            ("Docker", "Cloud_and_DevOps"), ("AWS", "Cloud_and_DevOps"),
            ("MLflow", "Tools_and_Practices"), ("Pandas", "Data_and_ML"),
            ("Statistics", "Data_and_ML"), ("Model Deployment", "Data_and_ML"),
        ],
        "SDE": [
            ("Python", "Programming"), ("Java", "Programming"),
            ("SQL", "Database"), ("REST API", "Web"),
            ("AWS", "Cloud_and_DevOps"), ("Docker", "Cloud_and_DevOps"),
            ("Git", "Tools_and_Practices"), ("Agile", "Tools_and_Practices"),
            ("Microservices", "Cloud_and_DevOps"), ("Spring Boot", "Web"),
        ],
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def normalize_role(title: str) -> str:
    if not title or not isinstance(title, str):
        return "Other"
    return ROLE_MAPPING.get(title.strip().lower(), "Other")


def get_tier(company_name: str) -> str:
    if not company_name or not isinstance(company_name, str):
        return "Other"
    return COMPANY_TIER_MAP.get(company_name.strip(), "Other")


def normalize_text(text: str) -> str:
    return text.title()


# ---------------------------------------------------------------------------
# Step 2: Adzuna seeding — query by company + role
# ---------------------------------------------------------------------------

def fetch_adzuna_for_company_role(
    company: str, role: str, app_id: str, app_key: str
) -> list[dict]:
    """Fetch up to 10 Adzuna results for a specific company + role query."""
    query = f"{role} {company}"
    url = (
        f"https://api.adzuna.com/v1/api/jobs/in/search/1"
        f"?app_id={app_id}&app_key={app_key}"
        f"&what={requests.utils.quote(query)}&results_per_page=10"
    )
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 429:
            time.sleep(2)
            resp = requests.get(url, timeout=3)
        if not resp.ok:
            return []
        return resp.json().get("results", [])
    except Exception:
        return []


def seed_via_adzuna(conn, app_id: str, app_key: str) -> tuple[int, int, int, set]:
    """Query Adzuna for each company × role combination. Returns (companies, roles, skills, unique_skills)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from db import insert_job_role, insert_role_skill, upsert_company, upsert_skill_frequency
    from skill_extractor import extract_skills

    company_count = 0
    role_count = 0
    skill_record_count = 0
    unique_skills: set[str] = set()

    # Sample 5 roles per company to keep under 3 minutes
    sample_roles = ["SDE", "Data Scientist", "ML Engineer", "DevOps Engineer", "Data Analyst"]

    total = len(COMPANY_TIER_MAP) * len(sample_roles)
    done = 0

    for company_name, tier in COMPANY_TIER_MAP.items():
        company_id = upsert_company(conn, company_name, tier, None)
        company_count += 1

        for role_title in sample_roles:
            results = fetch_adzuna_for_company_role(company_name, role_title, app_id, app_key)
            done += 1

            if done % 50 == 0:
                print(f"  [Adzuna] {done}/{total} queries done...")

            if not results:
                continue

            # Combine all descriptions for this company+role
            combined_text = f"{role_title} " + " ".join(
                r.get("description", "") or r.get("title", "") for r in results
            )
            skills = extract_skills(combined_text)
            if not skills:
                continue

            role_id = insert_job_role(conn, company_id, role_title, None)
            role_count += 1

            for skill_name, skill_category in skills:
                insert_role_skill(conn, role_id, skill_name, skill_category, "adzuna")
                upsert_skill_frequency(conn, skill_name, skill_category)
                skill_record_count += 1
                unique_skills.add(skill_name)

    conn.commit()
    print(f"[Adzuna] Done. Companies: {company_count} | Roles: {role_count} | Skills: {skill_record_count}")
    return company_count, role_count, skill_record_count, unique_skills


# ---------------------------------------------------------------------------
# Step 3: Guaranteed fallback — all 91 companies, no API needed
# ---------------------------------------------------------------------------

def seed_via_fallback(conn) -> tuple[int, int, int, set]:
    """Write hardcoded fallback data for every company. Never fails."""
    sys.path.insert(0, os.path.dirname(__file__))
    from db import insert_job_role, insert_role_skill, upsert_company, upsert_skill_frequency

    company_count = 0
    role_count = 0
    skill_record_count = 0
    unique_skills: set[str] = set()

    for company_name, tier in COMPANY_TIER_MAP.items():
        company_id = upsert_company(conn, company_name, tier, None)
        company_count += 1

        tier_skills = FALLBACK_SKILLS.get(tier, FALLBACK_SKILLS["Indian IT"])

        for role_title, skills in tier_skills.items():
            # Check if this company+role already has data
            existing = conn.execute(
                "SELECT COUNT(*) FROM job_roles jr "
                "JOIN companies c ON jr.company_id = c.company_id "
                "WHERE c.company_name = ? AND jr.role_title = ?",
                (company_name, role_title)
            ).fetchone()[0]
            if existing:
                continue

            role_id = insert_job_role(conn, company_id, role_title, None)
            role_count += 1

            for skill_name, skill_category in skills:
                insert_role_skill(conn, role_id, skill_name, skill_category, "fallback")
                upsert_skill_frequency(conn, skill_name, skill_category)
                skill_record_count += 1
                unique_skills.add(skill_name)

    conn.commit()
    print(f"[Fallback] Done. Companies: {company_count} | Roles: {role_count} | Skills: {skill_record_count}")
    return company_count, role_count, skill_record_count, unique_skills


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline() -> None:
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
    sys.path.insert(0, os.path.dirname(__file__))
    from db import create_schema, get_connection

    conn = get_connection()
    create_schema(conn)

    total_companies = 0
    total_roles = 0
    total_skill_records = 0
    all_unique_skills: set[str] = set()

    # --- Step 3: Guaranteed fallback FIRST — all 91 companies, always fast ---
    print("[Pipeline] Step 3: Running guaranteed fallback for all 91 companies...")
    c, r, s, u = seed_via_fallback(conn)
    total_companies = max(total_companies, c)
    total_roles += r
    total_skill_records += s
    all_unique_skills |= u

    # --- Step 2: Adzuna enrichment (best-effort, skip if slow) ---
    load_dotenv()
    app_id = os.environ.get("ADZUNA_APP_ID", "")
    app_key = os.environ.get("ADZUNA_APP_KEY", "")

    if app_id and app_key:
        print("[Pipeline] Step 2: Enriching via Adzuna API (best-effort)...")
        try:
            import threading
            result_box: list = []

            def _adzuna():
                result_box.append(seed_via_adzuna(conn, app_id, app_key))

            t = threading.Thread(target=_adzuna, daemon=True)
            t.start()
            t.join(timeout=90)  # max 90 seconds for Adzuna enrichment
            if result_box:
                c2, r2, s2, u2 = result_box[0]
                total_roles += r2
                total_skill_records += s2
                all_unique_skills |= u2
            else:
                print("[Pipeline] Adzuna timed out after 90s — fallback data is sufficient.")
        except Exception as e:
            print(f"[Pipeline] Adzuna enrichment skipped: {e}")
    else:
        print("[Pipeline] No Adzuna credentials — using fallback data only.")

    conn.close()

    print(
        f"Database write complete. "
        f"Companies: {total_companies} | "
        f"Roles: {total_roles} | "
        f"Skill records: {total_skill_records} | "
        f"Unique skills tracked: {len(all_unique_skills)}"
    )


if __name__ == "__main__":
    run_pipeline()
