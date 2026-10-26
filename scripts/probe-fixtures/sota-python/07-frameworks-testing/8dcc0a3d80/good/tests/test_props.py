from hypothesis import given, strategies as st


@given(st.integers(min_value=1))
def test_positive(n):
    assert sqrt_int(n * n) == n
