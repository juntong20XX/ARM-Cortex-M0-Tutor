"""
Basic tools for assemble.
"""
import itertools
from dataclasses import dataclass


@dataclass(frozen=True)
class ASMParam:
    """
    ASM code param
    """
    text: str
    type_name: str
    is_static: bool
    value: int = 0


@dataclass(frozen=True)
class ASMLine:
    """
    ASM code line
    """
    basic: str
    condition: str
    param: ASMParam
    param_1: ASMParam = ASMParam("", "", False, 0)
    param_2: ASMParam = ASMParam("", "", False, 0)

    def to_code(self, spaces=4):
        line = " " * spaces if isinstance(spaces, int) and spaces > 0 else ""
        line += self.basic
        line += self.condition
        line += " "
        line += ", ".join(i.text for i in itertools.takewhile(lambda x: x.type_name,
                                                              (self.param, self.param_1, self.param_2)))
        return line
