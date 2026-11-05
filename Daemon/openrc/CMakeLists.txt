set(OPENRC_INITDIR "${CMAKE_INSTALL_SYSCONFDIR}/init.d" CACHE PATH "OpenRC init script directory")
configure_file(ydotoold.service-openrc.in "${CMAKE_CURRENT_BINARY_DIR}/ydotoold" @ONLY)
install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/ydotoold" DESTINATION "${OPENRC_INITDIR}")
