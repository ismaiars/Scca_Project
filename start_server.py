#!/usr/bin/env python3
"""
Script de inicio para el servidor SCCA
"""

import sys
import os
from pathlib import Path

# Agregar el directorio backend al PYTHONPATH
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "core"))

# Ahora importar y ejecutar la aplicación
if __name__ == "__main__":
    from backend.main_app import main
    main()