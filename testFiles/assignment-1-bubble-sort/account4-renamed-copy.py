def bubble_sort(arr):
    length = len(arr)
    for outer in range(length):
        for inner in range(0, length - outer - 1):
            if arr[inner] > arr[inner + 1]:
                arr[inner], arr[inner + 1] = arr[inner + 1], arr[inner]
    return arr
