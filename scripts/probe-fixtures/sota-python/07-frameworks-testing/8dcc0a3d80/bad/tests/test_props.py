from hypothesis import given, strategies as st


@given(st.integers().filter(lambda n: n > 0))
def test_positive(n):
    assert sqrt_int(n * n) == n
