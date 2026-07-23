"""Тесты Pydantic-схем: ExperimentConfigCreate, VariantResponse.

Валидация:
  - name: 1-50 символов
  - variants: все веса > 0 (сумма НЕ обязана быть 100 — алгоритм нормализует)
  - config: опциональный Dict[str, Any]
  - url: опциональный, max 200 символов
  - is_active: bool, по умолчанию True
"""

import pytest
from pydantic import ValidationError
from src.schemas.experiment import ExperimentConfigCreate, VariantResponse


# ────────────────────────────────
# ExperimentConfigCreate
# ────────────────────────────────

class TestValidExperiments:
    """Валидные конфигурации — должны проходить."""

    def test_50_50(self):
        exp = ExperimentConfigCreate(name="test_50_50", variants={"A": 50, "B": 50})
        assert exp.name == "test_50_50"
        assert exp.variants == {"A": 50, "B": 50}
        assert exp.is_active is True
        assert exp.config is None
        assert exp.url is None

    def test_33_33_34(self):
        exp = ExperimentConfigCreate(
            name="three_variants",
            variants={"A": 33, "B": 33, "C": 34},
        )
        assert sum(exp.variants.values()) == 100

    def test_with_config(self):
        exp = ExperimentConfigCreate(
            name="with_config",
            variants={"blue": 50, "red": 50},
            config={
                "blue": {"title": "Blue theme"},
                "red": {"title": "Red theme"},
            },
        )
        assert exp.config["blue"]["title"] == "Blue theme"

    def test_with_url(self):
        exp = ExperimentConfigCreate(
            name="url_test",
            variants={"A": 100},
            url="/landing",
        )
        assert exp.url == "/landing"

    def test_single_variant(self):
        exp = ExperimentConfigCreate(name="single", variants={"A": 100})
        assert exp.variants == {"A": 100}

    def test_equal_weights_not_100(self):
        """Веса не обязаны суммироваться в 100 — алгоритм нормализует."""
        exp = ExperimentConfigCreate(name="eq", variants={"A": 33, "B": 33, "C": 33})
        assert sum(exp.variants.values()) == 99  # 33+33+33 = 99, но это ок

    def test_is_active_false(self):
        exp = ExperimentConfigCreate(
            name="disabled_test",
            variants={"A": 50, "B": 50},
            is_active=False,
        )
        assert exp.is_active is False


class TestInvalidExperiments:
    """Невалидные конфигурации — должны кидать ValidationError."""

    def test_negative_weight(self):
        with pytest.raises(ValidationError, match="положительн"):
            ExperimentConfigCreate(name="neg", variants={"A": -10, "B": 110})

    def test_zero_weight(self):
        with pytest.raises(ValidationError, match="положительн"):
            ExperimentConfigCreate(name="zero", variants={"A": 0, "B": 100})

    @pytest.mark.parametrize("name", ["", "a" * 51])
    def test_invalid_name_length(self, name):
        with pytest.raises(ValidationError):
            ExperimentConfigCreate(name=name, variants={"A": 100})

    def test_missing_variants_field(self):
        with pytest.raises(ValidationError):
            ExperimentConfigCreate(name="no_variants")  # type: ignore[call-arg]

    def test_empty_variants_dict(self):
        """Пустой словарь — нет ошибки, но 'control' на выдаче."""
        exp = ExperimentConfigCreate(name="empty", variants={})
        assert exp.variants == {}

    def test_all_negative_weights(self):
        with pytest.raises(ValidationError, match="положительн"):
            ExperimentConfigCreate(name="all_neg", variants={"A": -1, "B": -2})


# ────────────────────────────────
# VariantResponse
# ────────────────────────────────

class TestVariantResponse:
    def test_valid_response(self):
        resp = VariantResponse(
            experiment_name="test",
            user_id="user_1",
            variant="B",
        )
        assert resp.experiment_name == "test"
        assert resp.user_id == "user_1"
        assert resp.variant == "B"

    def test_control_variant(self):
        resp = VariantResponse(
            experiment_name="unknown",
            user_id="user_1",
            variant="control",
        )
        assert resp.variant == "control"

    def test_missing_user_id(self):
        with pytest.raises(ValidationError):
            VariantResponse(
                experiment_name="test",
                user_id="",  # пустая строка
                variant="A",
            )

    def test_long_experiment_name(self):
        """VariantResponse не ограничивает длину — проверяем что не падает."""
        resp = VariantResponse(
            experiment_name="x" * 200,
            user_id="user_1",
            variant="A",
        )
        assert len(resp.experiment_name) == 200
