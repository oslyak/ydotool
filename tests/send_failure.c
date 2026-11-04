#define main ydotool_client_main
#include "../Client/ydotool.c"
#undef main

int main(void) {
    int pair[2];
    if (socketpair(AF_UNIX, SOCK_DGRAM, 0, pair)) return 3;
    fd_daemon_socket = pair[0];
    close(pair[1]);
    uinput_emit(EV_KEY, KEY_A, 1, true);
    return 0;
}
