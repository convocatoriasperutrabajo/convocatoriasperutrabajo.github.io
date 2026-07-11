"""Compatibilidad de salida UTF-8 para consolas de Windows."""
import sys


def configurar_salida_utf8() -> None:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
