def parse_markdown_code_blocks(text):
    """Strip ``` fences from a markdown string and return inner code.

    ```python
    parse_markdown_code_blocks("```\nx = 1\n```")
    ```
    """
    out = []
    inside = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return "\n".join(out)
