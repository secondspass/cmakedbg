# Cmakedbg
Cmakedbg is a command-line debugger for CMake that can be run to debug your CMake build steps.

Similar to gdb, you can 
1. launch your CMake build under cmakedbg 
2. set breakpoints
3. step through the cmake steps line by line
4. show the listing to see which CMake file you're in
5. show the backtrace to see the CMake callstack
6. inspect CMake variables
7. pipe debugger command output to shell commands
8. and hopefully more useful things in the future 

This is useful for those of us that work mainly in the terminal and needed a gdb-like terminal tool
to help debug complicated CMake builds.

# Install from PyPI
```
pip install cmakedbg
```
or
```
pipx install cmakedbg
```

# How to install
1. Clone this repository and cd into it
2. Run `pip install .` (make sure you set up your virtual environment first, or use `pipx install .`
   to install it without needing to set up a virtual environment).
3. Once installed, `cmakedbg` command will be available on the command line.

## How to use
```
usage: cmakedbg [-h] [-v] --cmd cmake [OPTIONS ...]

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  --cmd cmake [OPTIONS ...]
                        cmake command with arguments to run debugger on
```

2. If you run your cmake build with `cmake ..` from the build directory, then to run your CMake run under cmakedbg, simply do
   `cmakedbg --cmd cmake ..`.  This will open a REPL. 
3. Set a breakpoint with `br /path/to/CMakeLists.txt:<lineno>` where `<lineno>` should be replaced
   with the appropriate line number. 
4. `run` command will start Cmake. CMake will now run till it hits the breakpoint
5. `next` and `step` will go to next line, and step into the function respectively, just like gdb.
6. Type `help` on the REPL to see what commands are available.
```
>>> help

CMake Debugger Commands:
=======================

Flow Control:
------------
breakpoint, break, br <file:line>    Set a breakpoint at specified file and line number
run, r                               Start the CMake build execution
continue, c                          Continue execution until next breakpoint
next, n                              Step over - execute next line without entering functions
step, s                              Step into - execute next line, entering functions if present

Information:
------------
info breakpoints        List all set breakpoints (aliases: info break, info b)
info variables          Display all CMake variables in current scope (aliases: info vars, info locals)
get variable <name>     Display value of specific CMake variable (alias: get var)
list                    Show source code around current line (aliases: listing, li, l)
stacktrace              Display current call stack (aliases: st, backtrace, bt)

Other:
------
pipe <cmakedbg command> | <shell command>     Pipe the output of a cmakedbg command to a shell
                                              command e.g. pipe info vars | less
quit, q                                       Exit the debugger
help, h                                       Display this help message

Notes:
- Many commands require the CMake build to be running first (start with 'run')
- Commands can use either full names or their shorter aliases
- Empty input will repeat the last command
- Unknown commands will display an error message
```

## Where this came from

CMake 3.27 onward, CMake has implemented the [Debug Adapter
Protocol](https://microsoft.github.io/debug-adapter-protocol/implementors/tools). This allows for
tools to hook into a running CMake process and step through the CMake configuration steps line by
line like you would with a programming language debugger. There is a plugin for VSCode that
leverages this to provide a editor integrated CMake GUI debugger through their CMake Tools
extension. But there is a need for a plain CLI debugger that we can use from the terminal like GDB,
which this fulfills.



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
- [x] add support for repeating last command when pressing "enter"
- [x] change globals to a dataclass 
- [ ] add types
- [ ] add support for an .rc file where you can set a breakpoint info that will be read by the
  cmakedbg on launch
- [x] account for the fact in the main while loop, that there are cases when receiving the
  stackframe response that the number of frames in the list can be more than 1.j
- [x] add ability to pipe output of cmakedbg command outputs to shell commands
- [ ] tests for pipe command, parse user output, other functions
- [x] figure out how to make this installable as a command line utility
- [x] publish to PyPI
- [ ] change how the list command works to be more aligned to gdb behavior
- [ ] refactor for readability, and add lots of tests
