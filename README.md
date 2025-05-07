# Cmakedbg

Cmakedbg is a command-line debugger for CMake that can be run to debug your CMake build steps.
Similar to gdb, you can launch your CMake build under cmakedbg, set breakpoints, step through the
cmake steps line by line, show the listing to see which CMake file you're in, show the backtrace to
see the CMake callstack, and hopefully more useful things. This is useful for those of us that work
mainly in the terminal and needed a gdb-like terminal tool to help debug complicated CMake builds.

## How to use

1. Clone the repository with `git clone`. 
2. If you run your cmake build with `cmake ..`, then to run your CMake run under cmakedbg, simply do
   `python3 /path/to/cmakedbg/cmakedbg --cmd cmake ..`.  This will open a REPL. 
3. Set a breakpoint with `br /path/to/CMakeLists.txt:<lineno>` where `<lineno>` should be replaced
   with the appropriate line number. 
4. Launch CMake with `run`. CMake will now run till it hits the breakpoint
5. `next` and `step` will go to next line, and step into the function respectively, just like gdb.
6. Type `help` on the REPL to see what commands are available.

## Where this came from

CMake 3.27 onward, CMake has implemented the [Debug Adapter
Protocol](https://microsoft.github.io/debug-adapter-protocol/implementors/tools). This allows for
tools to hook into a running CMake process and step through the CMake configuration steps line by
line like you would with a programming language debugger. There is a plugin for VSCode that
leverages this to provide a CMake GUI debugger through their CMake Tools extension. But there isn't
a plain CLI CMake debugger yet. UNTIL NOW!!! 



## TODOs:
- [x] implement printing out individual variables
- [x] launch cmake directly from debugger
- [x] add log levels and print json sends and recvs only for higher log levels (with -v|--verbose
  flag)
- [x] show listing at point
- [x] implementing 'next' (step over) and 'step into'
- [x] write help output
- [x] write man page
- [x] quit - with ctrl+d and with command 'quit'
- [x] add tests
- [ ] add support for repeating last command when pressing "enter"
- [x] change globals to a dataclass 
- [ ] add types
- [ ] add support for an .rc file where you can set a breakpoint info that will be read by the
  cmakedbg on launch
- [x] account for the fact in the main while loop, that there are cases when receiving the
  stackframe response that the number of frames in the list can be more than 1.j
