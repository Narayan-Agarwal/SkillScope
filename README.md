# SkillScope

> Job Market Intelligence Platform — discover what skills the market demands, explore company/role directories, and analyze your resume against real job data.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://skillscopeplatform.streamlit.app)

---

## Features

- **Skill Demand Dashboard** — top 20 skills by frequency, filterable by category and tier
- **Skill Heatmap** — role × skill-category heatmap with tier filtering
- **Tier Comparison** — grouped bar chart comparing top skills across 6 company tiers
- **AI & GenAI Trends** — dedicated chart for AI/GenAI skill prevalence with bar/pie toggle
- **Job Explorer** — browse 91 companies across 6 tiers, drill into roles and skill consensus charts
- **Resume Gap Analyzer** — upload your PDF resume, paste a JD, get a match score and prioritized gap skills

---

## Company Coverage

| Tier | Examples |
|---|---|
| Product | Google, Microsoft, Amazon, Meta, Apple, Netflix |
| Indian_IT | TCS, Infosys, Wipro, HCL, Tech Mahindra, Cognizant |
| Startup | Razorpay, Zepto, Meesho, Groww, CRED, Postman |
| EdTech | BYJU'S, Unacademy, Vedantu, upGrad, Simplilearn |
| Esports | Nodwin Gaming, WinZO, Mobile Premier League |
| Consulting | Deloitte, Accenture, McKinsey, BCG, PwC, EY |

---

## Tech Stack

- **Frontend**: Streamlit
- **Charts**: Plotly
- **Database**: SQLite (via stdlib `sqlite3`)
- **Data Sources**: Kaggle (LinkedIn Jobs 2024/2025), Adzuna API
- **PDF Parsing**: PyMuPDF + pdfplumber
- **Testing**: pytest + Hypothesis (property-based)

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/skillscope.git
cd skillscope

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
cp .env.example .env
# Edit .env and fill in your KAGGLE_API_TOKEN, ADZUNA_APP_ID, ADZUNA_APP_KEY

# 4. Seed the database
python src/seed_data.py

# 5. Launch the app
streamlit run app.py
```

---

## Project Structure

```
skillscope/
├── app.py                 # Streamlit entry point
├── seed_data.py           # Data pipeline CLI
├── skill_taxonomy.py      # 250+ skill definitions across 10 categories
├── skill_extractor.py     # Keyword-based skill matching
├── resume_parser.py       # PDF text extraction
├── db.py                  # SQLite CRUD layer
├── analytics.py           # Query and aggregation layer
├── pages/
│   ├── dashboard.py
│   ├── job_explorer.py
│   └── resume_analyzer.py
├── data/                  # gitignored — generated at runtime
├── tests/                 # pytest + Hypothesis test suite
├── .streamlit/
│   └── config.toml
├── .env.example
├── requirements.txt
└── LICENSE
```

---

## Data Sources

- **Kaggle**: [LinkedIn Job Postings 2024/2025](https://www.kaggle.com/datasets/arshkon/linkedin-job-postings) — requires a Kaggle API token
- **Adzuna**: [Adzuna Job Search API](https://developer.adzuna.com/) — free tier, requires app_id and app_key

---

## Streamlit Cloud Deployment

### 1. Push to GitHub

```bash
git add .
git commit -m "feat: complete SkillScope implementation"
git push origin main
```

### 2. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. Click **New app** → select your repo (`Narayan-Agarwal/SkillScope`), branch `main`, main file `app.py`.
3. Click **Advanced settings** → open the **Secrets** tab.
4. Paste the following (replace with your real values):

```toml
KAGGLE_API_TOKEN = "your_kaggle_api_token"
ADZUNA_APP_ID = "your_adzuna_app_id"
ADZUNA_APP_KEY = "your_adzuna_app_key"
```

5. Click **Deploy**.

> The app reads secrets via `get_secret(key)` which checks `st.secrets` first, then `os.environ` as fallback — so the same code works locally (via `.env`) and on Streamlit Cloud (via secrets).

### 3. Seed the Database on First Run

After deployment, open the Dashboard page and click **🔄 Refresh Data** to trigger the pipeline and populate the SQLite database.

> Note: Streamlit Cloud uses an ephemeral filesystem — the database resets on each redeployment. For persistent storage, consider mounting a volume or using a hosted SQLite service.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Narayan Agarwal**  
Department of Computer Science and Engineering  
B.Tech 2023–2027  
Veer Surendra Sai University of Technology, Burla
