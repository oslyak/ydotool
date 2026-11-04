#define _GNU_SOURCE
#include <stdarg.h>
#define main ydotool_client_main
#include "../Client/ydotool.c"
#undef main

int __real_connect(int fd, const struct sockaddr *address, socklen_t length);
int __real_open(const char *path, int flags, ...);

int __wrap_connect(int fd, const struct sockaddr *address, socklen_t length) {
    const struct sockaddr_un *sa = (const struct sockaddr_un *)address;
    FILE *log = fopen(getenv("TEST_PATH_LOG"), "a");
    if (!log) return -1;
    fprintf(log, "%s\n", sa->sun_path);
    fclose(log);
    if (strcmp(sa->sun_path, "/run/ydotoold/socket") == 0) {
        errno = ENOENT;
        return -1;
    }
    if (strcmp(sa->sun_path, getenv("TEST_PACKAGE_SOCKET")) == 0) {
        if (getenv("TEST_PACKAGE_MISSING")) { errno = ENOENT; return -1; }
        if (getenv("TEST_PACKAGE_DENIED")) { errno = EACCES; return -1; }
        struct sockaddr_un mapped = {.sun_family = AF_UNIX};
        snprintf(mapped.sun_path, sizeof(mapped.sun_path), "%s", getenv("TEST_REAL_SOCKET"));
        return __real_connect(fd, (const struct sockaddr *)&mapped, sizeof(mapped));
    }
    return __real_connect(fd, address, length);
}

int __wrap_open(const char *path, int flags, ...) {
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = va_arg(args, mode_t);
        va_end(args);
    }
    if (strcmp(path, getenv("TEST_PACKAGE_DIRECTORY")) == 0)
        path = getenv("TEST_REAL_DIRECTORY");
    return __real_open(path, flags, mode);
}

int main(int argc, char **argv) { return ydotool_client_main(argc, argv); }
