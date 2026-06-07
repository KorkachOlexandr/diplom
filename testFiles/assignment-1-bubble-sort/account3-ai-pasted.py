# Certainly! Here's the bubble_sort function you requested.
# Time complexity: O(n^2).
"""
This function takes a list and returns it sorted in ascending order using
the bubble sort algorithm.

I hope this helps! Let me know if you have any questions.
"""

```python
def bubble_sort(lst):
    n = len(lst)
    for i in range(n):
        for j in range(0, n - i - 1):
            if lst[j] > lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
    return lst
```

# Example usage:
print(bubble_sort([3, 1, 4, 1, 5]))
