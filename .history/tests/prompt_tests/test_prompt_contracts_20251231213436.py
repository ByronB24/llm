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


class TestPromptContracts(unittest.TestCase):
    def test_simple_prompt(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        repo_root = Path(__file__).parents[2]

        config_path = prompt_tests_dir / "promptfooconfig.yaml"
        test_path = prompt_tests_dir / "tests" / "simple.test.yaml"
        prompts_dir = repo_root / "prompts"

        if not config_path.exists():
            self.fail(f"Missing {config_path}")
        if not test_path.exists():
            self.fail(f"Missing {test_path}")
        if not prompts_dir.exists():
            self.fail(f"Missing prompts directory: {prompts_dir}")

        cli = _promptfoo_cli()
        if not cli:
            self.skipTest("promptfoo CLI not found. Install with `npm install -g promptfoo`.")

        openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if _looks_like_placeholder(openai_key):
            self.skipTest("OPENAI_API_KEY missing/placeholder; skipping promptfoo eval.")

        prompt_files = _prompt_files_from_config(config_path)
        if not prompt_files:
            self.fail(
                f"No prompt files found in {config_path}. "
                "Expected raw entries like file://../../prompts/something.yaml"
            )

        # Ensure every referenced file exists in repo_root/prompts
        for name in prompt_files:
            p = prompts_dir / name
            if not p.exists():
                self.fail(f"Prompt file referenced in config but not found: {p}")

        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        simple_prompt_cfg = None
        for p in cfg.get("prompts", []) or []:
            if isinstance(p, dict) and p.get("id") == "simple-echo":
                simple_prompt_cfg = p
                break
        if not simple_prompt_cfg:
            self.fail("Prompt id 'simple-echo' not found in promptfooconfig.yaml")

        test_cfg = yaml.safe_load(test_path.read_text(encoding="utf-8")) or {}
        tests = test_cfg.get("tests", [])
        if not tests:
            self.fail(f"No tests defined in {test_path}")

        env = dict(os.environ)
        env["OPENAI_API_KEY"] = openai_key

        # Write a temporary config with only the prompt under test and the API key inlined
        tmp_cfg_data = {
            "providers": [{"id": "openai:gpt-4", "config": {"apiKey": openai_key}}],
            "prompts": [simple_prompt_cfg],
            "tests": tests,
        }
        cfg_text = yaml.safe_dump(tmp_cfg_data, allow_unicode=False)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8", dir=config_path.parent
        ) as tmp_cfg:
            tmp_cfg.write(cfg_text)
            tmp_cfg_path = Path(tmp_cfg.name)

        cmd = [
            cli,
            "eval",
            "-c",
            str(tmp_cfg_path),
            "--no-cache",
            "--no-progress-bar",
            "--verbose",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=test_path.parent,
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
            + f"\nOUTPUT ({test_path.name}):\n"
            + (result.stdout or "")
            + "\n" + "=" * 100 + "\n"
        )

        self.assertEqual(result.returncode, 0, f"Promptfoo failed for {test_path.name}")


if __name__ == "__main__":
    unittest.main()
