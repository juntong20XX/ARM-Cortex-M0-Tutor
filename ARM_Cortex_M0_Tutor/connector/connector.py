#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Connect `server` and `data`.
"""
from .asm_basic import ASMLineReader, ASMLine

from dataclasses import dataclass

from pygdbmi import gdbcontroller

@dataclass(frozen=True)
class ASMStep:
    """
    Get the data obtained by stepping.

    .line_counter: The line number at which the current run ends is counted by `ALoader`.
    .addr_pc: a hex-number-like string
    .disassemble: (("address", <ASMLine>), ("address+", <ASMLine>), ...)
    .register_values example:
    Out: (('r0', '0x0'),
          ('r1', '0x255'),
          ('r2', '0x0'),
          ('r3', '0x0'),
          ('r4', '0x0'),
          ('r5', '0x0'),
          ('r6', '0x0'),
          ('r7', '0x0'),
          ('r8', '0x0'),
          ('r9', '0x0'),
          ('r10', '0x0'),
          ('r11', '0x0'),
          ('r12', '0x0'),
          ('r13', '0x200003f0'),
          ('r14', '0x51'),
          ('r15', '0x56'),
          ('N', '0'),
          ('Z', '1'),
          ('C', '0'),
          ('V', '0'))
    """
    line_counter: int
    addr_pc: str
    disassemble: tuple[tuple[str, ASMLine], ...]
    register_values: tuple[tuple[str, str], ...]


class ALoader:
    def __init__(self, gdbmi: gdbcontroller.GdbController, socket_path: str, asm_reader: ASMLineReader = None):
        """
        Connect gdb and get `disassemble` and `register_values` of assembly code.
        By iter this object, each time will get a `ASMStep` object.
        """
        self.gdbmi = gdbmi
        self._responses = gdbmi.get_gdb_response(timeout_sec=2)

        # connect
        response = gdbmi.write(f"-target-select remote {socket_path}")
        assert not self._command_failed(response)

        # step to ASM code
        gdbmi.write("-break-insert main")
        assert not self._command_failed(response)
        gdbmi.write("-exec-continue")
        self.gdbmi.write("-exec-step-instruction")

        if asm_reader is None:
            self.reader = ASMLineReader()
        else:
            self.reader = asm_reader

        self._line_counter = -1

    @staticmethod
    def _filter_type(response: list[dict], type_name: str):
        yield from (r for r in response if r.get("type") == type_name)

    def _command_failed(self, response):
        for r in self._filter_type(response, "result"):
            if r["message"] == "error":
                return True
            else:
                return False
        raise

    def is_running(self):
        return self.gdbmi.gdb_process is not None and self.gdbmi.gdb_process.poll() is None

    def get_disassemble(self, addr_pc: str) -> tuple[tuple[str, ASMLine], ...]:
        """

        :return: (("addr_pc-", ASMLine), ("addr_pc", ASMLine), ("addr_pc+", ASMLine))
        """
        response = self.gdbmi.write("-data-disassemble -a %s" % addr_pc)
        assert len(response) == 1
        # [{'type': 'result',
        #   'message': 'done',
        #   'payload': {'asm_insns': [{'address': '0x0000004a',
        #      'func-name': 'main',
        #      'offset': '0',
        #      'inst': 'push\t{r4, lr}'},
        #     {'address': '0x0000004c',
        #      'func-name': 'main',
        #      'offset': '2',
        #      'inst': 'bl\t0x54 <exec_asm>'},
        #     {'address': '0x00000050',
        #      'func-name': 'main',
        #      'offset': '6',
        #      'inst': 'pop\t{r4, pc}'}]},
        #   'token': None,
        #   'stream': 'stdout'}]
        d: dict[str, str]
        return tuple((d["address"], self.reader.load(d["inst"])) for d in response[0]["payload"]["asm_ins""ns"])

    @staticmethod
    def xpsr_hex_to_nzcv(xpsr: str) -> tuple[tuple[str, str], ...]:
        """
        """
        nzcv_bin = bin(int(xpsr, 16) >> 28)[2:].zfill(4)
        return tuple(zip("NZCV", nzcv_bin))

    def get_register_values(self):
        response = self.gdbmi.write("-data-list-register-values x")
        assert len(response) == 1
        register_values = response[0]["payload"]['register-values']
        xpsr = register_values[16]["value"]
        return tuple(("r" + r["number"], r["value"]) for r in register_values[:16]) + self.xpsr_hex_to_nzcv(xpsr)

    def asm_step(self) -> ASMStep:
        """

        :return:
        """
        # step instruction
        response = self.gdbmi.write("-exec-step-instruction")
        for r in self._filter_type(response, "notify"):
            payload = r["payload"]
            if (frame := payload.get("frame", {})).get("file", "").endswith((".s", ".S")):
                break
        else:
            # not in ASM file
            raise StopIteration
        # get disassemble
        addr_pc = frame["addr"]
        disassemble = self.get_disassemble(addr_pc)

        # get register values
        register_values = self.get_register_values()

        # add lene number
        self._line_counter += 1

        return ASMStep(self._line_counter, addr_pc, disassemble=disassemble, register_values=register_values)

    def __next__(self):
        return self.asm_step()

    def __iter__(self):
        return self

    def exit(self):
        if self.is_running():
            try:
                self.gdbmi.exit()
            except (ValueError, OSError):
                pass
        return not self.is_running()

    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    def __del__(self):
        self.exit()


