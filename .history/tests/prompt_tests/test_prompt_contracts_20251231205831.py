import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from dotenv import load_dotenv

# Do not overwrite real env vars with placeholders from .env
load_dotenv(override=False)


def _promptfoo_cli() -> str | None:
    return shutil.which("promptfoo.cmd") or shutil.which("promptfoo")


def _looks_like_placeholder(val: str) -> bool:
    v = (val or "").strip()
    return (not v) or v.startswith("${") or v.upper() in {"OPENAI_API_KEY", "YOUR_API_KEY_HERE", "CHANGEME"}


class TestPromptContracts(unittest.TestCase):
    def test_simple_prompt(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        repo_root = Path(__file__).parents[2]

        config_path = prompt_tests_dir / "promptfooconfig.yaml"
        test_path = prompt_tests_dir / "tests" / "simple.test.yaml"

        if not config_path.exists():
            self.fail(f"Missing {config_path}")
        if not test_path.exists():
            self.fail(f"Missing {test_path}")

        cli = _promptfoo_cli()
        if not cli:
            self.skipTest("promptfoo CLI not found. Install with `npm install -g promptfoo`.")

        openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if _looks_like_placeholder(openai_key):
            self.skipTest("OPENAI_API_KEY missing/placeholder; skipping promptfoo eval.")

        # These must exist in repo_root/prompts/
        required_prompt_files = [
            "simple.yaml",
            "content_clean.yaml",
            "chat_full.yaml",
            "information_extraction.yaml",
        ]

        prompts_dir = repo_root / "prompts"
        for name in required_prompt_files:
            p = prompts_dir / name
            if not p.exists():
                self.fail(f"Missing prompt file: {p}")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            # Copy YAML prompt files to temp dir so file://${PROMPT_TEMP_DIR}/X.yaml resolves.
            for name in required_prompt_files:
                shutil.copy2(prompts_dir / name, tmp_dir / name)

            env = dict(os.environ)
            env["OPENAI_API_KEY"] = openai_key
            env["PROMPT_TEMP_DIR"] = str(tmp_dir)

            cmd = [
                cli,
                "eval",
                "-c",
                str(test_path.resolve()),
                "--no-cache",
                "--no-progress-bar",
                "--verbose",
            ]

            result = subprocess.run(
                cmd,
                cwd=prompt_tests_dir,  # where promptfooconfig.yaml lives
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
            )

            print(
                "\n" + "=" * 100
                + f"\nOUTPUT ({test_path.name}):\n"
                + (result.stdout or "")
                + "\n" + "=" * 100 + "\n"
            )

            self.assertEqual(result.returncode, 0, f"Promptfoo failed for {test_path.name}")


if __name__ == "__main__":
    unittest.main()
