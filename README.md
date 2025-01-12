## TODOs:
- [x] implement printing out individual variables
- [x] launch cmake directly from debugger
- [ ] add log levels and print json sends and recvs only for higher log levels
- [ ] show listing at point
- [ ] implementing 'next' (step over) and 'step into'
- [ ] write help output
- [ ] write man page
- [x] quit - with ctrl+d and with command 'quit'
- [ ] add tests
- [x] change globals to a dataclass 
- [ ] add types
- [ ] add support for an .rc file where you can set a breakpoint info that will be read by the
  cmakedbg on launch
- [ ] account for the fact in the main while loop, that there are cases when receiving the
  stackframe response that the number of frames in the list can be more than 1.j
