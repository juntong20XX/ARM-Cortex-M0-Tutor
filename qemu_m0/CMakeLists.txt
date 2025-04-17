cmake_minimum_required(VERSION 3.12)
project(cortex-m0-microbit C)

# 完全禁用编译器特性检测
set(CMAKE_C_COMPILER_FORCED TRUE)
set(CMAKE_CXX_COMPILER_FORCED TRUE)

# 交叉编译设置
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)

# 核心编译选项
set(CPU_FLAGS -mcpu=cortex-m0 -mthumb)
set(COMMON_FLAGS
        ${CPU_FLAGS}
        -ffreestanding     # 独立环境
        -nostartfiles      # 不使用标准启动文件
        -nostdlib          # 禁用标准库
        -fno-builtin       # 禁用内置函数
        -Wno-builtin-declaration-mismatch  # 抑制警告
)

# 链接器选项
set(LINK_FLAGS
        ${CPU_FLAGS}
        -T "${CMAKE_SOURCE_DIR}/microbit.ld"
        -Wl,--gc-sections
        -Wl,-Map=${PROJECT_NAME}.map
        -specs=nano.specs   # 使用最小化库
)

# 应用全局选项
add_compile_options(${COMMON_FLAGS})
add_link_options(${LINK_FLAGS})

# 定义空系统调用桩函数（解决 CMake 测试需要）
file(WRITE ${CMAKE_BINARY_DIR}/syscalls.c "
void _exit(int status) { while(1); }
void _close(int fd) { }
int _lseek(int fd, int offset, int whence) { return 0; }
int _read(int fd, char* buf, int len) { return 0; }
int _write(int fd, const char* buf, int len) { return len; }
void* _sbrk(int incr) { extern char _end; static char* heap = &_end; char* prev = heap; heap += incr; return prev; }
")

# 添加可执行目标
add_executable(${PROJECT_NAME}.elf
        startup.c
        main.c
        ${CMAKE_BINARY_DIR}/syscalls.c
        syscalls.c  # 包含桩函数
)

# 后处理命令
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
        COMMAND arm-none-eabi-objcopy -O binary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
        COMMENT "生成二进制文件"
)

# QEMU 运行目标
add_custom_target(run
        COMMAND qemu-system-arm -M microbit -kernel $<TARGET_FILE:${PROJECT_NAME}.elf>
        DEPENDS ${PROJECT_NAME}.elf
        COMMENT "在 QEMU 中运行..."
)