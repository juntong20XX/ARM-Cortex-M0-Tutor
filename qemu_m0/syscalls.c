//
// Created by zhu on 25-4-18.
//
// syscalls.c 提供必要的最小系统调用实现
void _exit(int status) { while(1); }
void _close(int fd) { }
// ... 其他必要桩函数