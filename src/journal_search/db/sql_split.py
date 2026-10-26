"""Split a PostgreSQL script into single statements.

asyncpg rejects multiple commands in one prepared statement. Dollar-quoted
function bodies contain semicolons and must stay intact.
"""


def split_sql(script: str) -> list[str]:
    """Return executable statements, omitting comment-only fragments."""
    statements: list[str] = []
    current: list[str] = []
    i = 0
    length = len(script)
    dollar_tag: str | None = None
    in_single = False
    in_line_comment = False
    in_block_comment = False

    while i < length:
        char = script[i]
        nxt = script[i + 1] if i + 1 < length else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and nxt == "/":
                current.append("/")
                i += 2
                in_block_comment = False
                continue
            i += 1
            continue

        if dollar_tag is not None:
            if script.startswith(dollar_tag, i):
                current.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            current.append(char)
            i += 1
            continue

        if in_single:
            current.append(char)
            if char == "'" and nxt == "'":
                current.append("'")
                i += 2
                continue
            if char == "'":
                in_single = False
            i += 1
            continue

        if char == "-" and nxt == "-":
            current.append("--")
            i += 2
            in_line_comment = True
            continue

        if char == "/" and nxt == "*":
            current.append("/*")
            i += 2
            in_block_comment = True
            continue

        if char == "'":
            in_single = True
            current.append(char)
            i += 1
            continue

        if char == "$":
            tag_end = i + 1
            while tag_end < length and (script[tag_end].isalnum() or script[tag_end] == "_"):
                tag_end += 1
            if tag_end < length and script[tag_end] == "$":
                dollar_tag = script[i : tag_end + 1]
                current.append(dollar_tag)
                i = tag_end + 1
                continue

        if char == ";":
            statement = "".join(current).strip()
            if _is_executable(statement):
                statements.append(statement)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    tail = "".join(current).strip()
    if _is_executable(tail):
        statements.append(tail)
    return statements


def _is_executable(statement: str) -> bool:
    """True when the statement still contains SQL after line comments are removed."""
    if not statement:
        return False
    kept: list[str] = []
    for line in statement.splitlines():
        if line.strip().startswith("--"):
            continue
        kept.append(line)
    return bool("".join(kept).strip())
