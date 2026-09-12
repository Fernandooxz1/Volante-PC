import os
import sys

# Asegurar que la raíz del repositorio esté en sys.path para las pruebas unitarias
REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
