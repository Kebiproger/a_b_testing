"""Настройка путей для импорта src.* из тестов."""
import sys
from pathlib import Path

# Корень проекта (на уровень выше tests/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Добавляем src каждого микросервиса в sys.path
# Experiment API — основной модуль под тестами
EXPERIMENT_API_SRC = PROJECT_ROOT / "apps" / "experiment_api"

if str(EXPERIMENT_API_SRC) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_API_SRC))
