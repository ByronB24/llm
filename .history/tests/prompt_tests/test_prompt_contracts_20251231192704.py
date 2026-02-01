import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(override=True)

PROMPT_YAML_PATHS = {
    "content_cleaner": Path(__file__).parents[2] / "prompts" / "content_clean.yaml",
    "info_extraction": Path(__file__).parents[2] / "prompts" / "information_extraction.yaml",
    "advisor_chat": Path(__file__).parents[2] / "prompts" / "chat.yaml",
    "simple": Path(__file__).parents[2] / "prompts" / "simple.yaml",
}


def _build_prompt_from_yaml(src: Path, dest: Path) -> None:
    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    system = (data.get("system") or "").strip()
    user = (data.get("user") or "").strip()
    dest.write_text(f"{system}\n\n{user}\n", encoding="utf-8")


class TestPromptContracts(unittest.TestCase):
    def test_prompt_contracts(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        env_file_path = Path(__file__).parents[2] / ".env"
        promptfoo_bin = "promptfoo"

        # Fail fast with a clear instruction if the CLI is missing
        if not shutil.which(shlex.split(promptfoo_bin)[0]):
            self.fail(
                "promptfoo CLI not found. Install it (e.g. `pip install promptfoo` or `npm install -g promptfoo`) "
                "or set PROMPTFOO_BIN to the executable (e.g. 'npx promptfoo')."
            )

        config_path = (prompt_tests_dir / "promptfooconfig.yaml").resolve()
        if not config_path.exists():
            self.fail(f"promptfooconfig.yaml not found at {config_path}")

        test_configs = list((prompt_tests_dir / "tests").glob("*.test.yaml"))
        if not test_configs:
            self.fail("No promptfoo test files found in tests/*.test.yaml")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            # Build flattened prompt files from YAML sources for promptfoo
            built_prompts = {
                "content_cleaner": tmp_dir_path / "content_clean.txt",
                "info_extraction": tmp_dir_path / "information_extraction.txt",
                "advisor_chat": tmp_dir_path / "chat_full.txt",
                "simple": tmp_dir_path / "simple.txt",
            }
            for key, src in PROMPT_YAML_PATHS.items():
                if key not in built_prompts:
                    continue
                _build_prompt_from_yaml(src, built_prompts[key])

            run_env = {**os.environ, "PROMPT_TEMP_DIR": str(tmp_dir_path)}

            for path in test_configs:
                command = (
                    f'{promptfoo_bin} eval -c "{path.resolve()}" --env-file "{env_file_path}" '
                    f'--no-cache --no-progress-bar --no-table --verbose'
                )

                result = subprocess.run(
                    command,
                    cwd=prompt_tests_dir,
                    shell=True,
                    env=run_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )

                output = result.stdout.decode()
                print(
                    "\n"
                    + "=" * 100
                    + f"\nOUTPUT ({path.name}):\n"
                    + output
                    + "\n"
                    + "=" * 100
                    + "\n"
                )
                self.assertEqual(
                    result.returncode, 0, f"Promptfoo tests failed for {path.name}"
                )


if __name__ == "__main__":
    unittest.main()
