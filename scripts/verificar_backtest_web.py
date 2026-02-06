"""
Script de Verificación Pre-Ejecución: Backtest Web
Verifica que todo está configurado correctamente antes de ejecutar desde web.

Uso:
    python verificar_backtest_web.py
"""

import sys
import os
from pathlib import Path

# Intentar importar colorama, si no está disponible usar ANSI codes
try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    # Definir colores ANSI estándar
    class Fore:
        GREEN = '\033[32m'
        YELLOW = '\033[33m'
        RED = '\033[31m'
        CYAN = '\033[36m'
        WHITE = '\033[37m'
    class Back:
        BLUE = '\033[44m'
    class Style:
        RESET_ALL = '\033[0m'

def print_header(msg):
    print(f"\n{Back.BLUE}{Fore.WHITE} {msg} {Style.RESET_ALL}")

def print_success(msg):
    print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

def print_warning(msg):
    print(f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}")

def print_error(msg):
    print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")

def print_info(msg):
    print(f"{Fore.CYAN}ℹ️  {msg}{Style.RESET_ALL}")

# ... rest of verifier script available in repo ...
