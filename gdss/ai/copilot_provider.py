"""GitHub Copilot CLI provider for CI and developer workstations."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from gdss.logger import get_logger

logger = get_logger("gdss.ai.copilot_provider")


class CopilotCLIProvider:
    """Invokes GitHub Copilot CLI as a stateless inference provider.

    CRITICAL SAFETY GUARANTEE:
    Enforces `--deny-tool='*'` and `--no-ask-user` to ensure Copilot CLI CANNOT
    modify repository files, the active git checkout, or execute arbitrary shell
    commands. All proposed code patches are strictly emitted to stdout and
    returned to GDSS for ephemeral worktree sandbox validation.
    """

    def __init__(
        self,
        model: str | None = None,
        cache_dir: Path | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.model = model or os.getenv("COPILOT_MODEL") or "gpt-4o"
        self.cache_dir = cache_dir or Path(".gdss/llm_cache")
        self.timeout = timeout
        self._bin = self._find_binary()

    @staticmethod
    def _find_binary() -> str | None:
        """Locate the copilot CLI binary in PATH or via environment override."""
        custom_bin = os.getenv("COPILOT_BIN")
        if custom_bin and shutil.which(custom_bin):
            return custom_bin

        for name in ("copilot", "github-copilot"):
            path = shutil.which(name)
            if path:
                return path
        return None

    def is_available(self) -> bool:
        """Check whether the Copilot CLI binary is available on the system."""
        return self._bin is not None

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = -1) -> str:
        """Invoke Copilot CLI non-interactively with tools denied, returning stdout."""
        _ = (temperature, max_tokens)
        if not self._bin:
            raise RuntimeError(
                "Copilot CLI binary not found in PATH. Install via 'npm install -g @github/copilot' "
                "or configure OPENROUTER_API_KEY / AZURE_OPENAI_API_KEY."
            )

        cache_key = hashlib.sha256(f"copilot:{self.model}:{prompt}".encode()).hexdigest()
        cache_path = self.cache_dir / cache_key
        if cache_path.exists():
            logger.debug("LLM cache hit for Copilot CLI (key: %s)", cache_key[:8])
            return cache_path.read_text(encoding="utf-8")

        cmd = [
            self._bin,
            "-p",
            prompt,
            "--silent",
            "--no-ask-user",
            "--deny-tool=*",
        ]
        if self.model:
            cmd.extend(["--model", self.model])

        logger.info(
            "Executing Copilot CLI inference (model: %s, prompt_len: %d)",
            self.model,
            len(prompt),
        )
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            logger.warning("Copilot CLI inference timed out after %.1fs: %s", self.timeout, e)
            return ""
        except Exception as e:
            logger.warning("Copilot CLI execution failed: %s", e)
            return ""

        if res.returncode != 0:
            err_msg = res.stderr.strip() or res.stdout.strip()
            logger.warning(
                "Copilot CLI returned non-zero exit code %d: %s",
                res.returncode,
                err_msg,
            )
            return ""

        output = res.stdout.strip()
        if output:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(output, encoding="utf-8")
            except OSError:
                pass

        return output
