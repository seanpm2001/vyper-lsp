import re
from pathlib import Path

from vyper.compiler import CompilerData


def get_source(filepath):
    base_path = Path(__file__).parent.parent
    filepath = base_path / filepath
    return filepath.read_text()


def get_compiler_data(filepath):
    source = get_source(filepath)
    return CompilerData(source)


# detect if current line is a variable declaration
def is_var_declaration(line):
    # regex for variable declaration
    # should match lines starting with any identifier followed by a colon
    # like "foo: "
    reg = r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:"
    return bool(re.match(reg, line.strip()))


def is_attribute_access(line):
    # regex for attribute access
    # should match lines ending with a dot
    # like "foo."
    reg = r"\s*\.\s*$"
    return bool(re.match(reg, line.strip()))


def get_word_at_cursor(sentence: str, cursor_index: int) -> str:
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    while start > 0 and sentence[start - 1].isalnum():
        start -= 1

    # Find the end of the word
    while end < len(sentence) and sentence[end].isalnum():
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word