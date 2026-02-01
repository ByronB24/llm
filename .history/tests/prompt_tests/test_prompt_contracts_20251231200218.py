import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(override=True)


def _build_prompt_from_yaml(src: Path, dest: Path) -> None:
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    system = (data.get("system") or "").strip()
    user = (data.get("user") or "").strip()
    dest.write_text(f"{system}\n\n{user}\n", encoding="utf-8")


class TestPromptContracts(unittest.TestCase):
    def test_simple_prompt(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        env_file_path = Path(__file__).parents[2] / ".env"
        config_path = prompt_tests_dir / "promptfooconfig.yaml"
        simple_test_path = prompt_tests_dir / "tests" / "simple.test.yaml"
        simple_prompt_src = Path(__file__).parents[2] / "prompts" / "simple.yaml"

        if not os.environ.get("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY is required for promptfoo evaluations.")

        if not shutil.which("promptfoo"):
            self.fail(
                "promptfoo CLI not found. Install it (e.g. `npm install -g promptfoo` or `pip install promptfoo`)."
            )

        if not config_path.exists():
            self.fail(f"promptfooconfig.yaml not found at {config_path}")
        if not simple_test_path.exists():
            self.fail(f"simple.test.yaml not found at {simple_test_path}")
        if not simple_prompt_src.exists():
            self.fail(f"simple.yaml not found at {simple_prompt_src}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            simple_built = tmp_dir_path / "simple.txt"
            _build_prompt_from_yaml(simple_prompt_src, simple_built)

            run_env = {
                **os.environ,
                "PROMPT_TEMP_DIR": str(tmp_dir_path),
            }

            command = [
                "promptfoo",
                "eval",
                "-c",
                str(simple_test_path.resolve()),
                "--env-file",
                str(env_file_path),
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
                "\n"
                + "=" * 100
                + f"\nOUTPUT ({simple_test_path.name}):\n"
                + (result.stdout or "")
                + "\n"
                + "=" * 100
                + "\n"
            )

            self.assertEqual(
                result.returncode, 0, f"Promptfoo tests failed for {simple_test_path.name}"
            )


if __name__ == "__main__":
    unittest.main()
