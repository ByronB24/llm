import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(override=True)


def _build_prompt_from_yaml(src: Path) -> str:
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    system = (data.get("system") or "").strip()
    user = (data.get("user") or "").strip()
    return f"{system}\n\n{user}\n"


def _find_promptfoo_cli() -> str | None:
    # Prefer npm shim on Windows (avoids any stray python entrypoints)
    return shutil.which("promptfoo.cmd") or shutil.which("promptfoo")


def _looks_like_placeholder(val: str) -> bool:
    v = (val or "").strip()
    return (not v) or v.startswith("${") or v.upper() in {"OPENAI_API_KEY", "YOUR_API_KEY_HERE"}


class TestPromptContracts(unittest.TestCase):
    def test_simple_prompt(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        repo_root = Path(__file__).parents[2]

        config_path = prompt_tests_dir / "promptfooconfig.yaml"
        simple_test_path = prompt_tests_dir / "tests" / "simple.test.yaml"
        simple_prompt_src = repo_root / "prompts" / "simple.yaml"

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if _looks_like_placeholder(openai_key):
            self.skipTest("OPENAI_API_KEY is missing or a placeholder; skipping promptfoo eval.")

        promptfoo_cli = _find_promptfoo_cli()
        if not promptfoo_cli:
            self.skipTest("promptfoo CLI not found. Install with `npm install -g promptfoo`.")

        for p in (config_path, simple_test_path, simple_prompt_src):
            if not p.exists():
                self.fail(f"Required file not found: {p}")

        # Merge base config + test config, then inline the prompt so the eval is self-contained.
        base_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        test_config = yaml.safe_load(simple_test_path.read_text(encoding="utf-8")) or {}
        merged = {**base_config, **test_config}
        merged.pop("extends", None)

        prompt_text = _build_prompt_from_yaml(simple_prompt_src)
        merged["prompts"] = [
            {"id": "simple-echo", "label": "Simple Echo", "raw": prompt_text}
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            merged_config_path = tmp / "merged_simple.test.yaml"
            merged_config_path.write_text(yaml.safe_dump(merged, sort_keys=False), encoding="utf-8")

            run_env = {
                **os.environ,
                # Force the exact key promptfoo should use (even if something else exists)
                "OPENAI_API_KEY": openai_key.strip(),
            }

            command = [
                promptfoo_cli,
                "eval",
                "-c",
                str(merged_config_path),
                "--no-cache",
                "--no-progress-bar",
                "--verbose",
            ]

            result = subprocess.run(
                command,
                cwd=prompt_tests_dir,
                env=run_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )

            print(
                "\n" + "=" * 100
                + f"\nOUTPUT ({simple_test_path.name}):\n"
                + (result.stdout or "")
                + "\n" + "=" * 100 + "\n"
            )

            self.assertEqual(result.returncode, 0, f"Promptfoo tests failed for {simple_test_path.name}")


if __name__ == "__main__":
    unittest.main()
