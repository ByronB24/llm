import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Don't overwrite real env vars with placeholders from .env
load_dotenv(override=False)


PROMPT_TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = Path(__file__).parents[2]
CONFIG_PATH = PROMPT_TESTS_DIR / "promptfooconfig.yaml"
PROMPTS_DIR = REPO_ROOT / "prompts"


def _promptfoo_cli() -> str | None:
    # Prefer npm shim on Windows
    return shutil.which("promptfoo.cmd") or shutil.which("promptfoo")


def _looks_like_placeholder(val: str) -> bool:
    v = (val or "").strip()
    return (not v) or v.startswith("${") or v.upper() in {"OPENAI_API_KEY", "YOUR_API_KEY_HERE", "CHANGEME"}


def _prompt_files_from_config(config_path: Path) -> list[str]:
    """
    Reads promptfooconfig.yaml and extracts filenames referenced as:
      raw: file://<path>/<filename>
    """
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    prompts = cfg.get("prompts", []) or []

    files: list[str] = []
    for p in prompts:
        if not isinstance(p, dict):
            continue
        raw = (p.get("raw") or "").strip()
        if raw.startswith("file://"):
            try:
                files.append(Path(raw.removeprefix("file://")).name)
            except Exception:
                continue
    return files


def _load_prompt(cfg: dict, prompt_id: str) -> dict:
    for p in cfg.get("prompts", []) or []:
        if isinstance(p, dict) and p.get("id") == prompt_id:
            return p
    raise KeyError(f"Prompt id '{prompt_id}' not found in promptfooconfig.yaml")


def _providers_with_api_key(cfg: dict, api_key: str) -> list[dict]:
    providers = []
    for provider in cfg.get("providers", []) or []:
        if not isinstance(provider, dict):
            continue
        prov_copy = dict(provider)
        conf = dict(prov_copy.get("config") or {})
        conf["apiKey"] = api_key
        prov_copy["config"] = conf
        providers.append(prov_copy)
    if not providers:
        providers = [{"id": "openai:gpt-4", "config": {"apiKey": api_key}}]
    return providers


def _combined_config(prompt_id: str, test_path: Path, api_key: str) -> tuple[Path, Path]:
    """
    Returns (tmp_config_path, working_dir) for promptfoo to run.
    """
    base_cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    test_cfg = yaml.safe_load(test_path.read_text(encoding="utf-8")) or {}

    prompt_entry = _load_prompt(base_cfg, prompt_id)

    tests = test_cfg.get("tests", [])
    if not tests:
        raise AssertionError(f"No tests defined in {test_path}")

    merged_cfg = {k: v for k, v in test_cfg.items() if k not in {"extends", "prompt", "prompts", "providers"}}
    merged_cfg["providers"] = _providers_with_api_key(base_cfg, api_key)
    merged_cfg["prompts"] = [prompt_entry]
    merged_cfg["tests"] = tests

    cfg_text = yaml.safe_dump(merged_cfg, allow_unicode=False)
    tmp_dir = CONFIG_PATH.parent
    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8", dir=tmp_dir
    ) as tmp_cfg:
        tmp_cfg.write(cfg_text)
        tmp_cfg_path = Path(tmp_cfg.name)
    return tmp_cfg_path, test_path.parent


def _run_prompt_test(prompt_id: str, test_filename: str) -> subprocess.CompletedProcess[str]:
    if not CONFIG_PATH.exists():
        raise AssertionError(f"Missing {CONFIG_PATH}")
    if not PROMPTS_DIR.exists():
        raise AssertionError(f"Missing prompts directory: {PROMPTS_DIR}")

    cli = _promptfoo_cli()
    if not cli:
        raise unittest.SkipTest("promptfoo CLI not found. Install with `npm install -g promptfoo`.")

    openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if _looks_like_placeholder(openai_key):
        raise unittest.SkipTest("OPENAI_API_KEY missing/placeholder; skipping promptfoo eval.")

    prompt_files = _prompt_files_from_config(CONFIG_PATH)
    if not prompt_files:
        raise AssertionError(
            f"No prompt files found in {CONFIG_PATH}. Expected raw entries like file://../../prompts/something.yaml"
        )

    for name in prompt_files:
        if not (PROMPTS_DIR / name).exists():
            raise AssertionError(f"Prompt file referenced in config but not found: {PROMPTS_DIR / name}")

    test_path = PROMPT_TESTS_DIR / "tests" / test_filename
    if not test_path.exists():
        raise AssertionError(f"Missing {test_path}")

    tmp_cfg_path, workdir = _combined_config(prompt_id, test_path, openai_key)

    cmd = [
        cli,
        "eval",
        "-c",
        str(tmp_cfg_path),
        "--no-cache",
        "--no-progress-bar",
        "--verbose",
    ]

    env = dict(os.environ)
    env["OPENAI_API_KEY"] = openai_key

    try:
        result = subprocess.run(
            cmd,
            cwd=workdir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
    finally:
        tmp_cfg_path.unlink(missing_ok=True)

    print(
        "\n" + "=" * 100
        + f"\nOUTPUT ({test_filename}):\n"
        + (result.stdout or "")
        + "\n" + "=" * 100 + "\n"
    )

    return result


class TestContentCleaner(unittest.TestCase):
    def test_clean(self):
        result = _run_prompt_test("content-cleaner", "clean.test.yaml")
        self.assertEqual(result.returncode, 0, "Promptfoo failed for clean.test.yaml")


class TestAdvisorChat(unittest.TestCase):
    def test_chat(self):
        result = _run_prompt_test("advisor-chat", "chat.test.yaml")
        self.assertEqual(result.returncode, 0, "Promptfoo failed for chat.test.yaml")


class TestInformationExtraction(unittest.TestCase):
    def test_information_extraction(self):
        result = _run_prompt_test("info-extraction", "information_extraction.test.yaml")
        self.assertEqual(result.returncode, 0, "Promptfoo failed for information_extraction.test.yaml")


if __name__ == "__main__":
    unittest.main()
