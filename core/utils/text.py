from typing import List


def dedent(string: str) -> str:
    result = ""
    for line in string.splitlines(keepends=True):
        result += line.lstrip()
    return result


class S:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        if abs(v) != 1:
            return f"{v} {plural}"
        return f"{v} {singular}"


def to_pages(
    content: str, *, max_page_size: int = 1900, by_lines: bool = True
) -> List[str]:
    """Paginate a long string into a list of strings."""
    new_pages, index = [""], 0
    if by_lines:
        for line in content.splitlines(keepends=True):
            if len(new_pages[index] + line) > max_page_size:
                index += 1
                new_pages.append("")
            new_pages[index] += line

    else:
        while len(content) > max_page_size:
            new_pages.append(content[:max_page_size])
            content = content[max_page_size:]
        if content:
            new_pages.append(content)

    return new_pages
