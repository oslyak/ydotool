find_package(PkgConfig QUIET)

# Try to get the systemd directory for system/user units from the package
# and fall back on upstream default without the '/usr' prefix if not forced by
# command line.
if(PkgConfig_FOUND AND NOT DEFINED SD_UNITDIR)
    pkg_check_modules(SYSTEMD QUIET systemd)
endif()
if(SYSTEMD_FOUND AND NOT DEFINED SD_UNITDIR)
    if(SYSTEMD_USER_SERVICE)
        pkg_get_variable(SD_UNITDIR systemd systemduserunitdir)
    elseif(SYSTEMD_SYSTEM_SERVICE)
        pkg_get_variable(SD_UNITDIR systemd systemdsystemunitdir)
    endif()
endif()

if(NOT DEFINED SD_UNITDIR)
    if(SYSTEMD_USER_SERVICE)
        set(SD_UNITDIR "lib/systemd/user")
    else()
        set(SD_UNITDIR "lib/systemd/system")
    endif()
endif()

message("Systemd service file is going to be installed at ${SD_UNITDIR}")

configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/ydotoold.service.in"
    "${PROJECT_BINARY_DIR}/ydotoold.service"
    @ONLY)
install(FILES "${PROJECT_BINARY_DIR}/ydotoold.service" DESTINATION ${SD_UNITDIR})
