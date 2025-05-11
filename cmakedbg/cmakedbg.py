import socket
import argparse
import time
import shutil
import uuid
import sys
from sys import stdout
import subprocess
import pathlib
import json
from pprint import pprint
from dataclasses import dataclass
import dataclasses
import logging


# importing readline so input() will do better editing
# linter will warn readline is imported but unused
import readline

SEQ = 0
logger = logging.getLogger(__name__)


@dataclass
class DebuggerState():
    response: bytes = b""
    cmake_process_handle: subprocess.Popen = None
    host: str = f"/tmp/cmake-{uuid.uuid4()}"
    already_running: bool = False
    cmake_variables: dict = dataclasses.field(default_factory=dict)
    top_level_vars: int = 0
    current_line: (str, int) = ("", 0)
    stacktrace: list = dataclasses.field(default_factory=list)
    breakpoints: list = dataclasses.field(default_factory=list)
    last_command: str = ""


# TODO: move the payload functions to a different file
def send_request(s, request_func, *args):
    payload = request_func(*args)
    request_bytes = create_request(payload)

    logger.info(request_bytes)
    try:
        s.sendall(request_bytes)
    except Exception as e:
        raise e


def create_request(payload):
    global SEQ
    SEQ = SEQ + 1
    payload['seq'] = SEQ
    payload['type'] = 'request'
    payloadstr = json.dumps(payload)
    request = f"""Content-Length: {len(payloadstr)}\r
\r
{payloadstr}"""
    request_bytes = request.encode()
    return request_bytes


def recv_response(s, response):
    while b"\r\n\r\n" not in response:
        response = response + s.recv(4096)
    header, response = response.split(b"\r\n\r\n", maxsplit=1)
    header = header.decode()
    size = int(header.split()[1])  # geting content lenght value
    while len(response) < size:
        response = response + s.recv(4096)
    body, response = response[:size], response[size:]
    body_json = json.loads(body.decode())
    logger.info(header)
    logger.info(body_json)
    return body_json, response


def print_listing(filepath, linenum):
    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
        linenum = linenum - 1
        print(f"{filepath}:")
        if linenum - 2 >= 0:
            print(f"   {linenum - 1}: {lines[linenum - 2]}")
        if linenum - 1 >= 0:
            print(f"   {linenum}: {lines[linenum - 1]}")
        print(f"-> {linenum + 1}: {lines[linenum]}")
        if linenum + 1 < len(lines):
            print(f"   {linenum + 2}: {lines[linenum + 1]}")
        if linenum + 2 < len(lines):
            print(f"   {linenum + 3}: {lines[linenum + 2]}")

# debugger commands


def initialize():
    payload = {
        "command": 'initialize',
        'arguments': {
            'adapterID': "blah",
            'clientID': 'cmakecmdlinedebugger',
            'clientName': 'cmakecmdlinedebugger',
            'linesStartAt1': True,
            'columnsStartAt1': True,
            'locale': 'en_US',
            'pathFormat': 'path',
        }
    }
    return payload


def set_breakpoints(filepath, lineno):
    payload = {
        'command': 'setBreakpoints',
        'arguments': {
            'source': {
                'name': filepath,
                'path': filepath
            },
            'breakpoints': [
                {'line': lineno},
            ]
        }
    }
    return payload


def get_breakpoints():
    payload = {
        'command': 'breakpointLocations',
        'arguments': {},
    }
    return payload


def stacktrace():
    payload = {
        'command': 'stackTrace',
        'arguments': {
            'threadId': 1,
        }
    }
    return payload


def dbg_next():
    payload = {
        'command': 'next',
        'arguments': {
            'threadId': 1,
        }
    }
    return payload


def step_into():
    payload = {
        'command': 'stepIn',
        'arguments': {
            'threadId': 1,
        }
    }
    return payload


def scopes(stackFrame_id):
    payload = {
        'command': 'scopes',
        'arguments': {'frameId': stackFrame_id}
    }
    return payload


def variables(variablesReference_id):
    payload = {
        'command': 'variables',
        'arguments': {'variablesReference': variablesReference_id}
    }
    return payload


def dbg_continue():
    payload = {
        'command': 'continue',
        'arguments': {
            'threadId': 1,
        }
    }
    return payload


def configuration_done():
    payload = {
        'command': 'configurationDone',
        'arguments': {}
    }
    return payload


def validate_filepath_and_linenum(filepath_and_linenum: str) -> tuple[str, int]:
    filepathsplit = filepath_and_linenum.split(":")
    if len(filepathsplit) > 2:
        raise RuntimeWarning(
            "User error: breakpoint should be of the form '/path/to/file:linenumber'")
    if len(filepathsplit) == 2:
        try:
            filepath, linenum = filepathsplit[0], int(filepathsplit[1])
        except ValueError:
            raise ValueError(
                f"User error: line number is not a valid integer in {filepath_and_linenum}")
    else:
        filepath, linenum = filepathsplit[0], 1
    filepath = pathlib.Path(filepath).expanduser().resolve()
    if filepath.is_file():
        return str(filepath), linenum
    else:
        raise RuntimeWarning(f"User error: {filepath} is not a valid file")


def dbg_quit(debugger_state: DebuggerState):
    print()
    debugger_state.cmake_process_handle.kill()
    sys.exit(0)


def process_user_input(debugger_state) -> tuple[callable, list[any]]:
    if debugger_state.current_line != ("", 0):
        print_listing(*debugger_state.current_line)

    while True:
        try:
            user_input = input(">>> ").strip().split()
        except KeyboardInterrupt:  # catches CTRL+C
            print("\nKeyboardInterrupt")
            continue
        except EOFError:  # catches CTRL+D
            dbg_quit(debugger_state)


        if (debugger_command_and_args := parse_command(debugger_state, user_input)) is not None:
            return debugger_command_and_args
        


def parse_command(debugger_state: DebuggerState, user_input: str) -> tuple[callable, list[any]] | None: 

#    if "pipe" in user_input and "|" in user_input:
#
#        cmakedbg_command = user_input[1,user_input.index('|')]
#        shell_command = 
#
#    else:
#        print("Invalid syntax for pipe command")
#        return

    match user_input:
        case ["pipe", *rest]:
            # TODO: finish working on the pipe command
            rest = " ".join(rest)
            if "|" not in rest:
                print("Invalid syntax for pipe command")
                return
            dbg_command, shell_command = rest.split("|")
            dbg_command = shlex.split(dbg_command)
            shell_command = shlex.split(shell_command)

    
        case ["breakpoint" | "break" | "br", filepath_and_linenum]:
            try:
                filepath, linenum = validate_filepath_and_linenum(filepath_and_linenum)
            except RuntimeWarning as r:
                print(r)
                return
            except ValueError as e:
                print(e)
                return
            debugger_state.breakpoints.append((filepath, linenum))
            return set_breakpoints, [filepath, linenum]
        case ["run" | "r"]:
            if debugger_state.already_running:
                print("CMake already started running. Ignoring command.")
            else:
                return configuration_done, []
        case ["continue" | "c"]:
            if not debugger_state.already_running:
                print("CMake build has not started running. Use 'run' command to start running")
            else:
                return dbg_continue, []
        case ['next' | 'n']:
            if not debugger_state.already_running:
                print(
                    "CMake build has not started running. Use 'run' command to start running")
            else:
                return dbg_next, []
        case ['step' | 's']:
            if not debugger_state.already_running:
                print(
                    "CMake build has not started running. Use 'run' command to start running")
            else:
                return step_into, []
    
        case ["info", "breakpoints" | "break" | "b"]:
            pprint(debugger_state.breakpoints)
        case ["info", "variables" | "vars" | "locals"]:
            if not debugger_state.already_running:
                print(
                    "CMake build has not started running. Cannot print any variables yet. Use 'run' command to start running")
            else:
                pprint(debugger_state.cmake_variables)
        case ["get", "variable" | "var", varname]:
            if not debugger_state.already_running:
                print(
                    "CMake build has not started running. Cannot print any variables yet. Use 'run' command to start running")
            elif varname in debugger_state.cmake_variables:
                print(
                    f"{varname}={debugger_state.cmake_variables[varname]}")
            else:
                print(f"{varname}=")
        case ["list" | "listing" | "li" | "l"]:
            if debugger_state.current_line == ("", 0):
                print("CMake build has not started running or hit a breakpoint yet")
            else:
                print_listing(*debugger_state.current_line)
        case ["stacktrace" | "st" | "backtrace" | "bt"]:
            if not debugger_state.already_running:
                print(
                    "CMake build has not started running. Cannot print stacktrace. Use 'run' command to start running")
            else:
                pprint(debugger_state.stacktrace)
    
        case ["quit" | "q"]:
            dbg_quit(debugger_state)
        case ["help" | "h"]:
            print_debugger_commands()
    
        case []:
            return
        case _:
            print("Unknown command")

def print_debugger_commands():
    print("""
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
quit, q              Exit the debugger
help, h              Display this help message

Notes:
- Many commands require the CMake build to be running first (start with 'run')
- Commands can use either full names or their shorter aliases
- Empty input will be ignored
- Unknown commands will display an error message
          """)


def launch_cmake(cmd: list, pipe_host, print_help):

    if len(cmd) == 0:
        print_help()
        sys.exit(1)
    if "cmake" not in cmd[0]:
        print("Invalid format")
        print_help()
        sys.exit(1)
    if shutil.which(cmd[0]) is None:
        print("cmake is not in your PATH. Make sure cmake is installed and in your PATH")
        sys.exit(1)
    cmd[0] = shutil.which(cmd[0])
    cmd.insert(1, f"--debugger-pipe {pipe_host}")
    cmd.insert(1, "--debugger")
    print(f"cmd: {cmd}")
    cmd_handle = subprocess.Popen(cmd)
    time.sleep(0.5)
    return cmd_handle


def main():
    debugger_state = DebuggerState()
    # TODO: add argparsing to get the -v|--verbose flag
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true", default=False)
    parser.add_argument("--cmd", help="cmake command with arguments to run debugger on",
                        action="store", nargs="+", metavar=("cmake", "OPTIONS"), required=True)
    args = parser.parse_args()
    if args.verbose:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARN

    logging.basicConfig(stream=sys.stdout, level=loglevel)
    debugger_state.cmake_process_handle = launch_cmake(args.cmd, debugger_state.host,
                                                       parser.print_help)
    logger.info(debugger_state.cmake_process_handle)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:

        s.connect(debugger_state.host)
        debugger_state.response = b""

        send_request(s, initialize)

        while True:
            body_json, debugger_state.response = recv_response(s, debugger_state.response)
            match body_json:
                case {"type": "response", "command": "initialize"}:
                    pass
                case {"type": "event", "event": "initialized"}:
                    request_func, args = process_user_input(debugger_state)
                    send_request(s, request_func, *args)
                case {"type": "response", "command": "setBreakpoints"}:
                    request_func, args = process_user_input(debugger_state)
                    send_request(s, request_func, *args)
                case {"type": "response", "command": "configurationDone"}:
                    debugger_state.already_running = True
                case {"type": "event", "event": "stopped"}:
                    send_request(s, stacktrace)
                case {"type": "response", "command": "stackTrace",
                      "body": {"stackFrames": [{"id": frame_id, "line": linenumber, "source":
                                                {"path": filepath}} as first_frame, *other_frames]}}:
                    send_request(s, scopes, frame_id)
                    debugger_state.current_line = (filepath, linenumber)
                    debugger_state.stacktrace = [first_frame, *other_frames]
                case {"type": "response", "command": "scopes",
                      "body": {"scopes": [{"variablesReference": var_ref}]}}:
                    send_request(s, variables, var_ref)
                case {"type": "response", "command": "variables"}:
                    for variable in body_json['body']['variables']:
                        debugger_state.cmake_variables[variable['name']] = variable['value']
                        if variable['name'] in ['CacheVariables', 'Directories', 'Locals']:
                            debugger_state.top_level_vars = debugger_state.top_level_vars + 1
                            send_request(s, variables, variable['variablesReference'])
                    if debugger_state.top_level_vars > 0:
                        debugger_state.top_level_vars = debugger_state.top_level_vars - 1
                        continue

                    request_func, args = process_user_input(debugger_state)
                    send_request(s, request_func, *args)

                case {"type": "event", "event": "terminated"}:
                    dbg_quit(debugger_state)

                case _:  # Default case if no other case is matched
                    # Consider logging this for debugging.
                    print(f"Unhandled message type: {body_json}")
                    pass


if __name__ == '__main__':
    main()
