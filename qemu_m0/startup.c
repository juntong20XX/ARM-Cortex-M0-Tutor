#include <stdint.h>

// 定义中断向量表结构
typedef void (*vector_table_entry_t)(void);

// 声明外部 main 函数
extern int main(void);

// 定义默认中断处理函数
void Default_Handler(void) {
    while(1);
}

// 硬件复位处理函数
void Reset_Handler(void) {
    // 在调用 main 之前可以进行一些初始化工作
    // 例如：拷贝数据段、初始化 BSS 段等
    
    // 直接跳转到 main 函数
    main();
    
    // 如果 main 返回，进入无限循环
    while(1);
}

// 定义弱别名属性的中断处理函数
#define WEAK_ALIAS(x) __attribute__((weak, alias(#x)))

// 一些常见的异常处理函数
void NMI_Handler(void) WEAK_ALIAS(Default_Handler);
void HardFault_Handler(void) WEAK_ALIAS(Default_Handler);
void SVC_Handler(void) WEAK_ALIAS(Default_Handler);
void PendSV_Handler(void) WEAK_ALIAS(Default_Handler);
void SysTick_Handler(void) WEAK_ALIAS(Default_Handler);

// 中断向量表
__attribute__((section(".isr_vector")))
const vector_table_entry_t interrupt_vector_table[] = {
    // ARM Cortex-M0 异常向量表
    (vector_table_entry_t)0x20000400,  // 栈指针初始值（根据具体内存大小调整）
    Reset_Handler,
    NMI_Handler,
    HardFault_Handler,
    0,                  // 保留
    0,                  // 保留
    0,                  // 保留
    0,                  // 保留
    0,                  // 保留
    0,                  // 保留
    0,                  // 保留
    SVC_Handler,
    0,                  // 保留
    0,                  // 保留
    PendSV_Handler,
    SysTick_Handler
};
