"""
PBT: Retry com backoff exponencial em falhas de API.

Propriedade 12: Tasks com retry usam backoff correto (30s, 2min, 10min).
Valida: Requisitos 4.6, 6.4
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from integrations.tasks import WEBHOOK_RETRY_DELAYS


class TestRetryBackoff:
    """Propriedade 12: Backoff exponencial."""

    def test_retry_delays_are_increasing(self):
        """Delays de retry são crescentes."""
        assert WEBHOOK_RETRY_DELAYS == [30, 120, 600]
        for i in range(1, len(WEBHOOK_RETRY_DELAYS)):
            assert WEBHOOK_RETRY_DELAYS[i] > WEBHOOK_RETRY_DELAYS[i - 1]

    @given(
        retry_num=st.integers(min_value=0, max_value=2),
    )
    @settings(max_examples=5)
    def test_retry_delay_for_attempt(self, retry_num):
        """Cada tentativa usa o delay correto."""
        expected = {0: 30, 1: 120, 2: 600}
        delay = WEBHOOK_RETRY_DELAYS[min(retry_num, len(WEBHOOK_RETRY_DELAYS) - 1)]
        assert delay == expected[retry_num]

    @given(
        retry_num=st.integers(min_value=3, max_value=10),
    )
    @settings(max_examples=5)
    def test_retry_beyond_max_uses_last_delay(self, retry_num):
        """Tentativas além do máximo usam o último delay."""
        delay = WEBHOOK_RETRY_DELAYS[min(retry_num, len(WEBHOOK_RETRY_DELAYS) - 1)]
        assert delay == 600
