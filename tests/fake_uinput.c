#define _GNU_SOURCE
#include <fcntl.h>
#include <linux/uinput.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>

static int device_fd = -1;

int open(const char *path, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, mode_t);
        va_end(args);
    }
    if (strcmp(path, "/dev/uinput") == 0) {
        device_fd = syscall(SYS_openat, AT_FDCWD, getenv("TEST_UINPUT"), O_WRONLY | O_CREAT | O_APPEND, 0600);
        return device_fd;
    }
    return syscall(SYS_openat, AT_FDCWD, path, flags, mode);
}

int ioctl(int fd, unsigned long request, ...) {
    if (fd != device_fd) return -1;
    if (request == UI_SET_EVBIT || request == UI_SET_KEYBIT) {
        va_list args;
        va_start(args, request);
        uint64_t record[] = {request, va_arg(args, int)};
        va_end(args);
        syscall(SYS_write, atoi(getenv("TEST_SETUP_FD")), record, sizeof(record));
    }
    if (request == UI_DEV_CREATE) syscall(SYS_write, atoi(getenv("TEST_NOTIFY_FD")), "R", 1);
    return 0;
}

ssize_t write(int fd, const void *buffer, size_t length) {
    ssize_t result = syscall(SYS_write, fd, buffer, length);
    if (fd == device_fd) syscall(SYS_write, atoi(getenv("TEST_NOTIFY_FD")), "E", 1);
    return result;
}

unsigned int sleep(unsigned int seconds) {
    return 0;
}
