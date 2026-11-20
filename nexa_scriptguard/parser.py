from bisect import bisect_right
from dataclasses import dataclass, field

from .limits import ScanLimits
from .model import Location


class ParserUnavailable(RuntimeError):
    pass


class ParseLimitError(RuntimeError):
    pass


@dataclass(eq=False)
class SyntaxNode:
    kind: str
    location: Location
    source: bytes
    start_byte: int
    end_byte: int
    children: list["SyntaxNode"] = field(default_factory=list)
    has_error: bool = False
    parent: "SyntaxNode | None" = field(default=None, repr=False)

    @property
    def text(self):
        return self.source[self.start_byte : self.end_byte].decode("utf-8")


@dataclass
class BashDocument:
    source: bytes
    root: SyntaxNode
    node_count: int
    errors: list[Location]
    parser_name: str = "tree-sitter-bash"

    def walk(self):
        stack = [self.root]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))


def _position(source: bytes, line_starts: list[int], offset: int):
    row_index = bisect_right(line_starts, offset) - 1
    prefix = source[line_starts[row_index] : offset]
    return row_index + 1, len(prefix.decode("utf-8")) + 1


def parse_bash(data: bytes, limits: ScanLimits) -> BashDocument:
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Input is not valid UTF-8 at byte {exc.start}") from exc
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_bash
    except ImportError as exc:
        raise ParserUnavailable(
            "The Bash parser is not installed. Install the declared project dependencies "
            "or explicitly select --compat-heuristics."
        ) from exc

    language = Language(tree_sitter_bash.language())
    parser = Parser(language)
    tree = parser.parse(data)
    line_starts = [0]
    line_starts.extend(i + 1 for i, byte in enumerate(data) if byte == 10)
    count = 0
    errors = []
    converted: dict[int, SyntaxNode] = {}
    stack = [(tree.root_node, False)]
    while stack:
        original, visited = stack.pop()
        if not visited:
            count += 1
            if count > limits.max_ast_nodes:
                raise ParseLimitError(
                    f"Parser node limit exceeded ({limits.max_ast_nodes})"
                )
            stack.append((original, True))
            stack.extend((child, False) for child in reversed(original.children))
            continue
        start_line, start_column = _position(
            data, line_starts, original.start_byte
        )
        end_line, end_column = _position(data, line_starts, original.end_byte)
        location = Location(start_line, start_column, end_line, end_column)
        if original.is_error or original.is_missing:
            errors.append(location)
        children = [converted[child.id] for child in original.children]
        node = SyntaxNode(
            kind=original.type,
            location=location,
            source=data,
            start_byte=original.start_byte,
            end_byte=original.end_byte,
            children=children,
            has_error=original.has_error,
        )
        for child in children:
            child.parent = node
        converted[original.id] = node
    return BashDocument(
        source=data,
        root=converted[tree.root_node.id],
        node_count=count,
        errors=errors,
    )
