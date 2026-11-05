#pragma once

#include <errno.h>
#include <libintl.h>
#include <locale.h>
#include <stdlib.h>

static inline const char *ydotool_gettext(const char *message) {
    int saved_errno = errno;
    const char *translated = gettext(message);
    errno = saved_errno;
    return translated;
}
#define _(message) ydotool_gettext(message)
#define YDOTOOL_TEXTDOMAIN "ydotool"

static inline void ydotool_init_locale(void) {
    setlocale(LC_ALL, "");
    const char *dir = getenv("YDOTOOL_LOCALEDIR");
    if (!dir || !*dir) dir = getenv("TEXTDOMAINDIR");
    bindtextdomain(YDOTOOL_TEXTDOMAIN, dir && *dir ? dir : YDOTOOL_LOCALEDIR);
    textdomain(YDOTOOL_TEXTDOMAIN);
}
