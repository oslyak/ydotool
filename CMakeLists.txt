cmake_minimum_required(VERSION 3.22)
project(ydotool C)

set(CMAKE_C_STANDARD 11)

# Include GNU install directory module to detect where to install
# files on Linux/Unix systems (e.g., lib vs lib64)
include(GNUInstallDirs)

if(NOT DEFINED YDOTOOL_VERSION)
    execute_process(COMMAND git describe --tags --long --always
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        RESULT_VARIABLE RC_GIT_VER OUTPUT_VARIABLE GIT_VERSION)
else()
    set(RC_GIT_VER 0)
    set(GIT_VERSION "${YDOTOOL_VERSION}")
endif()

if (${RC_GIT_VER} EQUAL 0)
    string(STRIP ${GIT_VERSION} GIT_VERSION)
    message("-- Version: " ${GIT_VERSION})
    add_definitions(-DVERSION=\"${GIT_VERSION}\")
endif()

set(SOURCE_FILES_DAEMON Daemon/ydotoold.c)
set(SOURCE_FILES_CLIENT Client/ydotool.c Client/tool_click.c Client/tool_mousemove.c Client/tool_type.c Client/tool_key.c Client/tool_stdin.c)

add_executable(ydotoold ${SOURCE_FILES_DAEMON})
install(TARGETS ydotoold DESTINATION ${CMAKE_INSTALL_BINDIR})

add_executable(ydotool ${SOURCE_FILES_CLIENT})
install(TARGETS ydotool DESTINATION ${CMAKE_INSTALL_BINDIR})

add_subdirectory(Daemon)
add_subdirectory(manpage)

option(YDOTOOL_TESTS "Build isolated input test fixtures" OFF)
if(YDOTOOL_TESTS)
    add_library(fake_uinput SHARED tests/fake_uinput.c)
    list(REMOVE_ITEM SOURCE_FILES_CLIENT Client/ydotool.c)
    add_executable(send_failure tests/send_failure.c ${SOURCE_FILES_CLIENT})
    add_executable(socket_paths tests/socket_paths.c ${SOURCE_FILES_CLIENT})
    target_link_options(socket_paths PRIVATE -Wl,--wrap=connect -Wl,--wrap=open)
endif()
