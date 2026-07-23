"""Тесты ядра A/B тестирования — детерминированное распределение (SHA-256).

Алгоритм:
  hash = SHA-256(f"{user_id}:{experiment_name}")
  bucket = int(hash, 16) % 10000 / 100.0   # → 0.00 .. 99.99
  scaled = bucket / 100.0 * sum(weights)
  cumulative = 0
  for variant, weight in variants:
      cumulative += weight
      if scaled < cumulative → return variant
  return "control"
"""

from src.services.allocation import get_user_variant


class TestDeterministic:
    """Один и тот же user_id → всегда один и тот же вариант."""

    def test_same_user_same_variant(self):
        v1 = get_user_variant("user_123", "test_exp", {"A": 50, "B": 50})
        for _ in range(100):
            v2 = get_user_variant("user_123", "test_exp", {"A": 50, "B": 50})
            assert v1 == v2, (
                f"Детерминизм нарушен: первый раз {v1}, потом {v2}"
            )

    def test_different_users_may_differ(self):
        """Разные пользователи — необязательно разные варианты, но проверяем,
        что функция не падает и возвращает допустимые варианты."""
        results = set()
        for i in range(100):
            v = get_user_variant(f"user_{i}", "test_exp", {"A": 50, "B": 50})
            assert v in ("A", "B"), f"Неизвестный вариант: {v}"
            results.add(v)
        # Хотя бы 1 из 2 вариантов встретился (с 100 юзерами — почти гарантированно оба)
        assert len(results) >= 1

    def test_all_three_variants_appear(self):
        """С 1000 пользователями все 3 варианта (33/33/34) должны появиться."""
        results = set()
        for i in range(1000):
            v = get_user_variant(f"user_{i}", "three_test", {"A": 33, "B": 33, "C": 34})
            results.add(v)
        assert results == {"A", "B", "C"}, f"Не все варианты появились: {results}"


class TestDistribution:
    """Статистическая проверка: веса распределения соблюдаются."""

    def test_5050_within_tolerance(self):
        """На 10 000 пользователей разброс не более ±3% (300 юзеров) от 5000."""
        N = 10_000
        a_count = 0
        for i in range(N):
            v = get_user_variant(f"stat_user_{i}", "stat_exp", {"A": 50, "B": 50})
            if v == "A":
                a_count += 1

        expected = N // 2
        tolerance = 300  # 3%
        assert abs(a_count - expected) < tolerance, (
            f"Слишком большой разброс: A={a_count}/{N}, "
            f"ожидалось {expected}±{tolerance}"
        )

    def test_uneven_weights(self):
        """70/30 — грубая проверка: A ≈ 70%."""
        N = 10_000
        a_count = 0
        for i in range(N):
            v = get_user_variant(f"uneven_{i}", "uneven_exp", {"A": 70, "B": 30})
            if v == "A":
                a_count += 1

        ratio = a_count / N
        assert 0.65 < ratio < 0.75, (
            f"Пропорция A={ratio:.3f}, ожидалось ~0.70"
        )


class TestEdgeCases:
    """Граничные случаи."""

    def test_empty_variants(self):
        """Пустой словарь → 'control'."""
        v = get_user_variant("user_1", "exp", {})
        assert v == "control"

    def test_single_variant(self):
        """Один вариант со 100 → он же."""
        v = get_user_variant("user_1", "exp", {"A": 100})
        assert v == "A"

    def test_33_33_33_equal_weights(self):
        """Три равных веса (33,33,33) — все три варианта выдаются."""
        results = set()
        for i in range(2000):
            v = get_user_variant(f"eq_{i}", "eq_exp", {"A": 33, "B": 33, "C": 33})
            results.add(v)
        assert results == {"A", "B", "C"}, f"33/33/33: {results}"

    def test_same_user_different_experiments(self):
        """Один пользователь в разных экспериментах может получить разные варианты."""
        v1 = get_user_variant("user", "exp_1", {"A": 50, "B": 50})
        v2 = get_user_variant("user", "exp_2", {"A": 50, "B": 50})
        # Не обязательно разные, но тест не падает
        assert v1 in ("A", "B")
        assert v2 in ("A", "B")

    def test_weights_not_summing_to_100(self):
        """Веса не обязаны суммироваться в 100 — алгоритм нормализует.
        1+1+1 = 3, каждый получает ~33%."""
        results = set()
        for i in range(2000):
            v = get_user_variant(f"ns_{i}", "ns_exp", {"A": 1, "B": 1, "C": 1})
            results.add(v)
        assert results == {"A", "B", "C"}, f"1+1+1: {results}"
