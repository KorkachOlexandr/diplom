def fib(n, _cache={0: 0, 1: 1}):
    if n not in _cache:
        _cache[n] = fib(n - 1) + fib(n - 2)
    return _cache[n]
