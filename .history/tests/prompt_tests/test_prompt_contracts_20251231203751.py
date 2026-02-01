import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml
from dotenv import load_dotenv

# IMPORTANT: don't override real env vars with placeholders from .env
load_dotenv(override=False)


def _find_promptfoo_cli() -> str | None:
    # Prefer npm shim on Windows
    return shutil.which("promptfoo.cmd") or shutil.which("promptfoo")


def _is_placeholder(value: str) -> bool:
    v = (value or "").strip()
    # catches "${OPENAI_API_KEY}" and other placeholders
    return (not v) or v.startswith("${") or v.upper() in {"OPENAI_API_KEY", "YOUR_API_KEY_HERE", "CHANGEME"}


def _build_prompt_text_from_yaml(path: Path) -> str:
    """
    Expects YAML like:
      system: |
        ...
      user: |
        ...
    Produces: "<system>\\n\\n<user>\\n"
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    system = (data.get("system") or "").strip()
    user = (data.get("user") or "").strip()
    return f"{system}\n\n{user}\n"


def _read_prompt_source(repo_root: Path, base_name: str) -> str:
    """
    Try prompts/<base_name>.yaml first, then .prompt, then .txt.
    """
    candidates = [
        repo_root / "prompts" / f"{base_name}.yaml",
        repo_root / "prompts" / f"{base_name}.yml",
        repo_root / "prompts" / f"{base_name}.prompt",
        repo_root / "prompts" / f"{base_name}.txt",
    ]
    for p in candidates:
        if p.exists():
            if p.suffix in {".yaml", ".yml"}:
                return _build_prompt_text_from_yaml(p)
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"Could not find a prompt source for '{base_name}'. Tried: "
        + ", ".join(str(c) for c in candidates)
    )


class TestPromptContracts(unittest.TestCase):
    def test_simple_prompt(self):
        prompt_tests_dir = Path(__file__).parent.resolve()
        repo_root = Path(__file__).parents[2]

        # Your promptfoo config + the test suite file
        config_path = prompt_tests_dir / "promptfooconfig.yaml"
        simple_test_path = prompt_tests_dir / "tests" / "simple.test.yaml"

        # Verify required files exist
        if not config_path.exists():
            self.fail(f"promptfooconfig.yaml not found at {config_path}")
        if not simple_test_path.exists():
            self.fail(f"simple.test.yaml not found at {simple_test_path}")

        # Require a real OpenAI key
        openai_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if _is_placeholder(openai_key):
            self.skipTest(
                "OPENAI_API_KEY is missing or a placeholder (e.g. ${OPENAI_API_KEY}). "
                "Set a real key in your environment (recommended) or .env."
            )

        # Require promptfoo CLI
        promptfoo_cli = _find_promptfoo_cli()
        if not promptfoo_cli:
            self.skipTest("promptfoo CLI not found. Install with `npm install -g promptfoo`.")

        # Optional: sanity-check promptfoo runs
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

        # Build the exact temp files that your promptfooconfig.yaml expects:
        # file://${PROMPT_TEMP_DIR}/simple.txt
        # file://${PROMPT_TEMP_DIR}/content_clean.txt
        # file://${PROMPT_TEMP_DIR}/chat_full.txt
        # file://${PROMPT_TEMP_DIR}/information_extraction.txt
        prompt_file_map = {
            "simple.txt": "simple",
            "content_clean.txt": "content_clean",
            "chat_full.txt": "chat",  # expects prompts/chat.yaml or prompts/chat.prompt etc
            "information_extraction.txt": "information_extraction",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)

            # Write built prompt text files into PROMPT_TEMP_DIR
            for out_name, base_prompt in prompt_file_map.items():
                out_path = tmp_dir_path / out_name
                out_text = _read_prompt_source(repo_root, base_prompt)
                out_path.write_text(out_text, encoding="utf-8")

            run_env = dict(os.environ)
            run_env["PROMPT_TEMP_DIR"] = str(tmp_dir_path)
            run_env["OPENAI_API_KEY"] = openai_key  # force the real key

            command = [
                promptfoo_cli,
                "eval",
                "-c",
                str(simple_test_path.resolve()),
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
                result.returncode,
                0,
                f"Promptfoo tests failed for {simple_test_path.name}",
            )


if __name__ == "__main__":
    unittest.main()
