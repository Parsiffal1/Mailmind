from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def tracked_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def test_contributing_file_removed_and_not_linked():
    assert not (REPO_ROOT / "CONTRIBUTING.md").exists()
    for rel in ["README.md", "README.zh.md", "README.zh-CN.md"]:
        assert "CONTRIBUTING.md" not in read_text(REPO_ROOT / rel)


def test_issue_template_config_exists_and_is_tracked():
    config = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
    assert config.exists()
    assert ".github/ISSUE_TEMPLATE/config.yml" in tracked_files()
    text = read_text(config)
    assert "blank_issues_enabled: false" in text
    assert "SECURITY.md" in text


def test_readmes_keep_language_switch_links():
    assert "[English](README.md) | [中文](README.zh.md)" in read_text(REPO_ROOT / "README.md")
    assert "[English](README.md) | [中文](README.zh.md)" in read_text(REPO_ROOT / "README.zh.md")


def test_readmes_surface_visual_demo_and_navigation():
    en = read_text(REPO_ROOT / "README.md")
    zh = read_text(REPO_ROOT / "README.zh.md")
    for text in (en, zh):
        assert "docs/demo/gifs/mailmind_brand_hero.gif" in text
        assert "docs/demo/screenshots/01_tasks_overview.png" in text
        assert "docs/demo/screenshots/02_ai_search_answer.png" in text
        assert "docs/demo/screenshots/03_indexed_sources.png" not in text
        assert "docs/demo/gifs/hero_ai_search.gif" not in text
        assert "docs/demo/gifs/documents_and_settings.gif" not in text
    assert "## Quick Navigation" in en
    assert "## 快速导航" in zh
    assert "## Who This Is For" not in en
    assert "## 适合谁使用" not in zh
    assert "## What This Project Is" not in en
    assert "## 这个项目是什么" not in zh


def test_env_example_uses_clean_placeholder_values():
    env_example = read_text(REPO_ROOT / ".env.example")
    assert "credentials.json" in env_example
    assert "token.json" in env_example
    assert "ANTHROPIC_API_KEY=your_anthropic_api_key" in env_example
    assert "TELEGRAM_BOT_TOKEN=your_telegram_bot_token" in env_example
    assert "VOYAGE_API_KEY=your_voyage_api_key" in env_example
    assert "18|" not in env_example
    assert "22|" not in env_example
    assert "34|" not in env_example
