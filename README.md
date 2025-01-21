## TODOs:
- [x] implement printing out individual variables
- [x] launch cmake directly from debugger
- [ ] add log levels and print json sends and recvs only for higher log levels (with -v|--verbose
  flag)
- [x] show listing at point
- [x] implementing 'next' (step over) and 'step into'
- [x] write help output
- [x] write man page
- [x] quit - with ctrl+d and with command 'quit'
- [ ] add tests
- [ ] add support for repeating last command when pressing "enter"
- [x] change globals to a dataclass 
- [ ] add types
- [ ] add support for an .rc file where you can set a breakpoint info that will be read by the
  cmakedbg on launch
- [x] account for the fact in the main while loop, that there are cases when receiving the
  stackframe response that the number of frames in the list can be more than 1.j
