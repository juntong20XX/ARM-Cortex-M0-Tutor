import unittest

from app.kernel import ASMLineReader, ASMLine, ASMParam

class MyTestCase(unittest.TestCase):
    def test_something(self):
        loader = ASMLineReader()
        # ADDS r0, r2, #0xA
        aline = loader.load("ADDS r0, r2, #0xA")
        target = ASMLine("add", "s",
                         ASMParam("r0", "r"),
                         ASMParam("r2", "r"),
                         ASMParam("#0xa", "i"))
        self.assertEqual(aline, target)  # add assertion here
        # subs r2,  #12
        aline = loader.load("subs r12,  #12")
        target = ASMLine("sub", "s",
                         ASMParam("r12", "r"),
                         ASMParam("#12", "i"))
        self.assertEqual(aline, target)  # add assertion here
        # 'ldr\tr1, [pc, #4]\t@ (0x5c <exec_asm+8>)'
        aline = loader.load('ldr\tr1, [pc, #4]\t@ (0x5c <exec_asm+8>)')
        target = ASMLine("ldr", "",
                         ASMParam("r1", "r"),
                         ASMParam("[pc, #4]", "a"))
        self.assertEqual(aline, target)  # add assertion here


if __name__ == '__main__':
    unittest.main()
