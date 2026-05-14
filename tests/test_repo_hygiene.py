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


def test_readmes_use_market_sentinel_style_hero_structure():
    en = read_text(REPO_ROOT / "README.md")
    zh = read_text(REPO_ROOT / "README.zh.md")

    assert not en.startswith("# MailMind")
    assert not zh.startswith("# MailMind")

    clone_block = "```bash\ngit clone https://github.com/Parsiffal1/Mailmind.git && cd Mailmind\n```"

    for text in (en, zh):
        assert "<div align=\"center\">" in text
        assert "docs/demo/gifs/mailmind_brand_hero.gif" in text
        assert "docs/demo/screenshots/01_tasks_overview.png" in text
        assert "docs/demo/screenshots/02_ai_search_answer.png" in text
        assert clone_block in text
        assert "Demo walkthrough" not in text

    assert "Interface preview" in en
    assert "Install" in en
    assert "What it gives" in en
    assert "How it works" in en
    assert "Read next" in en
    assert "Example output" not in en

    assert "界面预览" in zh
    assert "安装" in zh
    assert "你能得到什么" in zh
    assert "它怎么工作" in zh
    assert "继续阅读" in zh
    assert "示例输出" not in zh


def test_readmes_use_clean_real_gmail_examples():
    en = read_text(REPO_ROOT / "README.md")
    zh = read_text(REPO_ROOT / "README.zh.md")
    for text in (en, zh):
        assert "ANTHROPIC_API_KEY=" in text
        assert "MAILMIND_GMAIL_CREDENTIALS=" in text
        assert "MAILMIND_GMAIL_TOKEN=" in text
        assert "TELEGRAM_BOT_TOKEN=" in text
        assert "your_a..._key" not in text
        assert "your_t...oken" not in text


def test_readmes_include_rag_benchmark_table():
    en = read_text(REPO_ROOT / "README.md")
    zh = read_text(REPO_ROOT / "README.zh.md")
    for text in (en, zh):
        assert "48.35%" in text
        assert "63.74%" in text
        assert "78.02%" in text
        assert "64.84%" in text
        assert "0.691" in text
        assert "+15.39 pp" in text
        assert "+19.78 pp" in text
        assert "+18.69 pp" in text
        assert "+0.169" in text


def test_env_example_uses_clean_placeholder_values_and_mailmind_repo_metadata():
    env_example = read_text(REPO_ROOT / ".env.example")
    assert "credentials.json" in env_example
    assert "token.json" in env_example
    assert "MAILMIND_GITHUB_REPO=https://github.com/Parsiffal1/Mailmind.git" in env_example
    assert "MAILMIND_GITHUB_TOKEN=" in env_example
    assert "ANTHROPIC_API_KEY=" in env_example
    assert "TELEGRAM_BOT_TOKEN=" in env_example
    assert "VOYAGE_API_KEY=" in env_example
    assert "ghp_" not in env_example
