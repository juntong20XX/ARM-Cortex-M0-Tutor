cmake_minimum_required(VERSION 3.12)
project(cortex-m0-microbit C)

# 设置交叉编译工具链
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)
set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

# 定义目标 MCU 参数
set(CPU_FLAGS "-mcpu=cortex-m0 -mthumb")
set(LINKER_SCRIPT "${CMAKE_SOURCE_DIR}/board/linker.ld")

# 公共编译选项
add_compile_options(
        ${CPU_FLAGS}
        -fno-common
        -ffunction-sections
        -fdata-sections
        -fno-exceptions
        -nostdlib
        -Os
)

# 链接选项
add_link_options(
        ${CPU_FLAGS}
        -T ${LINKER_SCRIPT}
        -specs=nosys.specs
        -Wl,--gc-sections
        -Wl,-Map=output.map
        -Wl,--cref
        -nostartfiles
)

# 添加可执行文件
add_executable(${PROJECT_NAME}.elf
        board/startup.c
        src/main.c  # 确保包含您的应用程序代码
)

# 链接后生成二进制文件（可选）
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
        COMMAND arm-none-eabi-objcopy -O binary ${PROJECT_NAME}.elf ${PROJECT_NAME}.bin
        COMMENT "Generating binary file"
)

# 自定义运行目标（通过 QEMU）
add_custom_target(run
        COMMAND qemu-system-arm -M microbit -kernel ${PROJECT_NAME}.elf
        DEPENDS ${PROJECT_NAME}.elf
        COMMENT "Running in QEMU..."
)