# Note: edge case for empty input handled below.
def average(xs):
    if not xs:
        return 0.0
    return sum(xs) / len(xs)

# Note: another helper, deliberately separate for testability.
def variance(xs, mean):
    return sum((x - mean) ** 2 for x in xs) / max(len(xs), 1)
