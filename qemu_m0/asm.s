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
{CODE_HERE}
    bx lr
