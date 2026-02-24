"""
Basic tools for assemble.
"""
import re
import itertools
from dataclasses import dataclass

KNOWN_COMMANDS = (
    ("ldr", ("",)),

    ("mov", ("", "s")),

    ("add", ("", "s")),
    ("sub", ("", "s")),

    ("lsl", ("", "s")),
    ("lsr", ("", "s")),
    ("asr", ("", "s")),

    ("b", ("", "al", "eq", "ne", "cs", "hs", "cc", "lo", "mi",
           "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le")),

    ("bl", ("",)),
    ("bx", ("",)),
)

KNOWN_PARAMS = (
    ("r", r"(?:r(?:1[0-5]|\d)|pc|lr|sp)"),
    ("i", r"#[+-]?(?:0[bB][01]+|0[oO][0-7]+|\d+|0[xX][0-9a-fA-F]+)"),
    ("c", r"=[+-]?(?:0[bB][01]+|0[oO][0-7]+|\d+|0[xX][0-9a-fA-F]+)"),
    ("a", r"\[\s*(?:r\d+|pc|lr|sp)\s*,\s*#-?\d+\s*\]")
)


@dataclass(frozen=True)
class ASMParam:
    """
    ASM code param
    """
    text: str
    type_name: str


@dataclass(frozen=True)
class ASMLine:
    """
    ASM code line
    auto check input
    """
    basic: str
    condition: str
    param: ASMParam = ASMParam("", "")
    param_1: ASMParam = ASMParam("", "")
    param_2: ASMParam = ASMParam("", "")

    def to_code(self, spaces=4):
        line = " " * spaces if isinstance(spaces, int) and spaces > 0 else ""
        line += self.basic
        line += self.condition
        line += " "
        line += ", ".join(i.text for i in itertools.takewhile(lambda x: x.type_name,
                                                              (self.param, self.param_1, self.param_2)))
        return line


class ASMLineReader:
    """
    convert assembly lines to formatted ASMLine object
    It can be integrated by passing in different parameters during initialization.
    """
    def __init__(self, *, known_commands=KNOWN_COMMANDS, known_params=KNOWN_PARAMS):
        """
        build regex
        """
        self._known_commands = known_commands
        self._known_params = known_params

        self.RE_SPLIT_CP = re.compile("[ \t]+")
        self.RE_SPLIT_COMMAND = re.compile(self._get_split_command_regex_pattern())
        self.RE_SPLIT_PARAMS = re.compile(self._get_split_params_regex_pattern())

    def _get_split_command_regex_pattern(self):
        patterns = []
        for com, cons in self._known_commands:
            pattern = com.join("()") + "(" + "|".join(con if con else "$" for con in cons) + ")"
            patterns.append(pattern)
        return "^(?:" + "|".join(patterns) + ")$"

    def _get_split_params_regex_pattern(self):
        patterns = []
        for _, p in self._known_params:
            patterns.append(p.join("()"))
        return "^(?:" + "|".join(patterns) + ")? *(?:, *(.+?)(?:\t.*)?$|$)"

    def load(self, line: str) -> ASMLine:
        """
        read `line` and return ASMLine object
        """

        # split to command and args
        command, args = self.RE_SPLIT_CP.split(line.strip().lower(), maxsplit=1)

        # command
        command = command.strip()
        m = self.RE_SPLIT_COMMAND.match(command)
        assert m, ValueError("unsupported command", command, line)
        basic, condition = (i for i in m.groups() if i is not None)

        # args
        params = []
        while args:
            args = args.strip()
            m = self.RE_SPLIT_PARAMS.match(args)
            if m is None:
                raise ValueError("known param", args)
            groups = m.groups()

            for i in range(len(self._known_params)):
                if groups[i] is not None:
                    text = groups[i]
                    break
            else:
                raise
            params.append(ASMParam(text, self._known_params[i][0]))

            args = groups[-1]
        return ASMLine(basic, condition, *params)
