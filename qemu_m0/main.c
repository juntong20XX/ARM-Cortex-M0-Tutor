int main(void) {
    register int result asm("r0");
    
    __asm volatile (
        ".syntax unified\n"
        "movs r0, #10\n"     // 初始化 r0 为 10
        "movs r1, #20\n"     // 初始化 r1 为 20
        "adds r0, r0, r1\n"  // 使用 adds 指令
    );
    
    // 死循环
    while (1) {
        // 可以在这里添加调试代码
    }
    return result;
}
