#!/usr/bin/env python3
"""
Script para mostrar trades en vivo sin necesidad de menú interactivo
"""

import subprocess
import sys
import json
import time
from pathlib import Path

# Importar el código que muestra los trades
sys.path.insert(0, str(Path(__file__).parent))
from run_all_leagues import MultiLeagueBot

# Crear instancia del bot
bot = MultiLeagueBot()

# Mostrar los trades en vivo directamente
print("\nObteniendo datos de trades en vivo...")
time.sleep(1)
bot.show_live_trades()
