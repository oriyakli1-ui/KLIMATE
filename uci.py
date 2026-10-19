"""Minimal blocking UCI client (plain ``subprocess``, no asyncio).

python-chess's engine API needs an asyncio subprocess loop, which Streamlit's event loop policy
does not provide on Windows. A tiny synchronous client works the same everywhere.
"""
from __future__ import annotations

import os
import re
import subprocess
from typing import Optional, Tuple

_SCORE = re.compile(r"score (cp|mate) (-?\d+)")
_PV = re.compile(r" pv (\S+)")


class UciError(RuntimeError):
    pass


class UciEngine:
    def __init__(self, path: str, threads: int = 1, hash_mb: int = 32) -> None:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            self._p = subprocess.Popen(
                [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1, creationflags=flags,
            )
        except OSError as exc:
            raise UciError(f"cannot start engine: {exc}") from exc
        self._send("uci")
        self._read_until("uciok")
        self._send(f"setoption name Threads value {threads}")
        self._send(f"setoption name Hash value {hash_mb}")
        self._send("isready")
        self._read_until("readyok")

    def _send(self, line: str) -> None:
        assert self._p.stdin is not None
        self._p.stdin.write(line + "\n")
        self._p.stdin.flush()

    def _read_until(self, prefix: str) -> list[str]:
        assert self._p.stdout is not None
        lines = []
        for raw in self._p.stdout:
            line = raw.strip()
            lines.append(line)
            if line.startswith(prefix):
                return lines
        raise UciError("engine closed unexpectedly")

    def analyse(self, fen: str, depth: int = 12) -> Tuple[Optional[int], str]:
        """Evaluate ``fen``. Returns ``(centipawns for White, best move UCI)``.

        Mate scores are mapped to +-1000 cp. cp is None when the engine reports no score.
        """
        self._send(f"position fen {fen}")
        self._send(f"go depth {depth}")
        lines = self._read_until("bestmove")
        best = lines[-1].split()[1] if len(lines[-1].split()) > 1 else ""
        score: Optional[int] = None
        for line in reversed(lines):
            m = _SCORE.search(line)
            if m:
                value = int(m.group(2))
                score = value if m.group(1) == "cp" else (1000 if value > 0 else -1000)
                break
        if score is not None and fen.split(" ")[1] == "b":  # UCI scores are for the side to move
            score = -score
        return score, ("" if best in ("(none)", "0000") else best)

    def close(self) -> None:
        try:
            self._send("quit")
            self._p.wait(timeout=2)
        except Exception:  # noqa: BLE001 - best effort shutdown
            self._p.kill()
