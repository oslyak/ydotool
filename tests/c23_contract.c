#include <stddef.h>

#if !defined(__STDC_VERSION__) || __STDC_VERSION__ <= 201710L
#error "ydotool requires C23"
#endif
#ifdef __STRICT_ANSI__
#error "ydotool requires GNU extensions for Linux/POSIX APIs"
#endif

static_assert(_Generic(nullptr, nullptr_t: true, default: false));
