import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import shutil

import yaml
from dotenv import load_dotenv

load_dotenv(override=True)


def _build_prompt_from_yaml(src: Path, dest: Path) -> None:
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    system = (data.get("system") or "").strip()
    user = (data.get("user") or "").strip()
    dest.write_text(f"{system}\n\n{user}\n", encoding="utf-8")


def _find_promptfoo_cli() -> str | None:
    """
    Prefer the npm-installed Windows shim (promptfoo.cmd) to avoid accidentally
    picking up a stale/broken Python entrypoint (promptfoo.exe) from Anaconda.
    """
    return shutil.which("promptfoo.cmd") or shutil.which("promptfoo")


class TestPromptContracts(unittest.TestCase):
    def test_simple_prompt(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        repo_root = Path(__file__).parents[2]
        env_file_path = repo_root / ".env"

        config_path = prompt_tests_dir / "promptfooconfig.yaml"
        simple_test_path = prompt_tests_dir / "tests" / "simple.test.yaml"
        simple_prompt_src = repo_root / "prompts" / "simple.yaml"

        if not os.environ.get("OPENAI_API_KEY"):
            self.skipTest("OPENAI_API_KEY is required for promptfoo evaluations.")

        promptfoo_cli = _find_promptfoo_cli()
        if not promptfoo_cli:
            self.skipTest(
                "promptfoo CLI not found. Install it with `npm install -g promptfoo` "
                "or run via `npx promptfoo@latest ...`."
            )

        # Optional: verify it actually runs (gives a clearer error than later failures)
        try:
            subprocess.run(
                [promptfoo_cli, "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as e:
            self.skipTest(f"promptfoo CLI found but not runnable: {e}")

        if not config_path.exists():
            self.fail(f"promptfooconfig.yaml not found at {config_path}")
        if not simple_test_path.exists():
            self.fail(f"simple.test.yaml not found at {simple_test_path}")
        if not simple_prompt_src.exists():
            self.fail(f"simple.yaml not found at {simple_prompt_src}")

        base_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        simple_config = yaml.safe_load(simple_test_path.read_text(encoding="utf-8")) or {}
        merged_config = {**base_config, **simple_config}
        merged_config.pop("extends", None)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            simple_built = tmp_dir_path / "simple.txt"
            _build_prompt_from_yaml(simple_prompt_src, simple_built)

            run_env = {
                **os.environ,
                "PROMPT_TEMP_DIR": str(tmp_dir_path),
            }

            merged_config_path = tmp_dir_path / "merged_simple.test.yaml"
            merged_config_path.write_text(
                yaml.safe_dump(merged_config, sort_keys=False),
                encoding="utf-8",
            )

            command = [
                promptfoo_cli,
                "eval",
                "-c",
                str(merged_config_path),
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
