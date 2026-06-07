# A small linear regression toy for a homework about how AI language models
# learn from data. As an AI language model would put it: minimize loss.
def fit(xs, ys):
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den
    return slope, mean_y - slope * mean_x
