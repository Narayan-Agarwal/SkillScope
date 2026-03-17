"""
Tests for configuration files — verifies required keys, packages, and gitignore entries.
Requirements: 15.1, 15.5, 17.1, 17.2, 17.3
"""
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------------------
# .streamlit/config.toml
# ---------------------------------------------------------------------------

def test_streamlit_config_exists():
    assert os.path.isfile(os.path.join(ROOT, '.streamlit', 'config.toml'))


def test_streamlit_config_primary_color():
    content = _read('.streamlit/config.toml')
    assert 'primaryColor' in content


def test_streamlit_config_max_upload_size():
    content = _read('.streamlit/config.toml')
    assert 'maxUploadSize' in content


def test_streamlit_config_gather_usage_stats():
    content = _read('.streamlit/config.toml')
    assert 'gatherUsageStats' in content


# ---------------------------------------------------------------------------
# .env.example
# ---------------------------------------------------------------------------

def test_env_example_exists():
    assert os.path.isfile(os.path.join(ROOT, '.env.example'))


def test_env_example_kaggle_api_token():
    content = _read('.env.example')
    assert 'KAGGLE_API_TOKEN' in content


def test_env_example_adzuna_app_id():
    content = _read('.env.example')
    assert 'ADZUNA_APP_ID' in content


def test_env_example_adzuna_app_key():
    content = _read('.env.example')
    assert 'ADZUNA_APP_KEY' in content


# ---------------------------------------------------------------------------
# requirements.txt
# ---------------------------------------------------------------------------

def test_requirements_exists():
    assert os.path.isfile(os.path.join(ROOT, 'requirements.txt'))


@pytest.mark.parametrize('package', [
    'streamlit',
    'pandas',
    'plotly',
    'PyMuPDF',
    'pdfplumber',
    'requests',
    'python-dotenv',
    'kaggle',
    'hypothesis',
])
def test_requirements_contains_package(package: str):
    content = _read('requirements.txt')
    assert package.lower() in content.lower(), f'requirements.txt missing: {package}'


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------

def test_gitignore_exists():
    assert os.path.isfile(os.path.join(ROOT, '.gitignore'))


def test_gitignore_excludes_kaggle_raw():
    content = _read('.gitignore')
    assert 'data/kaggle_raw.csv' in content


def test_gitignore_excludes_env():
    content = _read('.gitignore')
    assert '.env' in content


def test_gitignore_excludes_db():
    content = _read('.gitignore')
    assert 'data/skillscope.db' in content
