cmake_minimum_required(VERSION 3.12)

set(CMAKE_C_COMPILER_WORKS 1)
set(CMAKE_C_COMPILER_FORCED TRUE)

project(cortex-m0-microbit C)


# 强制指定交叉编译工具链
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)  # 避免编译器检测失败

# CPU 架构选项（作为独立参数）
set(CPU_ARCH "-mcpu=cortex-m0")
set(THUMB_MODE "-mthumb")

# 链接脚本路径
set(LINKER_SCRIPT "${CMAKE_SOURCE_DIR}/board/microbit.ld")

# 编译选项
add_compile_options(
        ${CPU_ARCH}
        ${THUMB_MODE}
        -fno-common
        -ffunction-sections
        -fdata-sections
        -fno-exceptions
        -nostdlib
        -Os
)

# 链接选项
add_link_options(
        ${CPU_ARCH}
        ${THUMB_MODE}
        -T "${LINKER_SCRIPT}"
        -specs=nosys.specs
        -Wl,--gc-sections
        -Wl,-Map=output.map
        -Wl,--cref
        -nostartfiles
        -Wl,--no-warn-rwx-segments  # 禁用警告 RWX segments
)

# 可执行文件
add_executable(${PROJECT_NAME}.elf
        board/startup.c
        src/main.c
)

# 生成二进制文件
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
        COMMAND arm-none-eabi-objcopy -O binary $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
        COMMENT "Generating binary file"
)

# QEMU 运行目标
add_custom_target(run
        COMMAND qemu-system-arm -M microbit -kernel $<TARGET_FILE:${PROJECT_NAME}.elf> -nographic -S -S
        DEPENDS ${PROJECT_NAME}.elf
        COMMENT "Running in QEMU..."
)