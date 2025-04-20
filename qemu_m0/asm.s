.syntax unified
.thumb
.cpu cortex-m0

/* 定义代码段 */
.section .text.asm_func, "ax"
.align 2

/* 导出符号 */
.global exec_asm
.thumb_func    /* 必须声明Thumb函数 */

/* 函数实现 */
exec_asm:
    /* 测试用加法指令（符合Thumb-1指令集） */
    adds r0, r0, r1    /* 正确写法：目标寄存器必须与第一个操作数相同 */
    bx lr              /* 正确返回指令 */