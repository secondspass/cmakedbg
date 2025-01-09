import socket
import time
import shutil
import uuid
import sys
import subprocess
import pathlib
import json
from pprint import pprint
from dataclasses import dataclass
import dataclasses

# importing readline so input() will do better editing
# linter will warn readline is imported but unused
import readline

HOST = "/tmp/cmake-blah"
SEQ = 0
ALREADY_RUNNING = False
SINGLE_VARIABLE = None
TOP_LEVEL_VARS = 0


@dataclass
class DebuggerState():
    response: bytes = b""
    cmake_process_handle: subprocess.Popen = None
    host: str = f"/tmp/cmake-{uuid.uuid4()}"
    seq: int = 0
    already_running: bool = False
    cmake_variables: dict = dataclasses.field(default_factory=dict)
    single_variable: str = ""
    top_level_vars: int = 0


def send_request(s, request_func, *args):
    payload = request_func(*args)
    request_bytes = create_request(payload)

    # TODO: change this to log instead
    print(request_bytes)
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
    print(header)
    pprint(body_json)
    print("", flush=True)
    return body_json, response


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


def validate_filepath_and_linenum(filepath_and_linenum: str):
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


def process_user_input(debugger_state):
    while True:
        try:
            user_input = input(">>> ").strip().split()
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")
            continue
        except EOFError:
            dbg_quit(debugger_state)

        match user_input:
            case ["set", "breakpoint" | "br", filepath_and_linenum]:
                try:
                    filepath, linenum = validate_filepath_and_linenum(filepath_and_linenum)
                except RuntimeWarning as r:
                    print(r)
                    continue
                except ValueError as e:
                    print(e)
                    continue

                return set_breakpoints, [filepath, linenum]
            case ["get", "breakpoint" | "br"]:
                return get_breakpoints, []
            case ["run" | "r"]:
                if debugger_state.already_running:
                    print("CMake already started running. Ignoring command.")
                else:
                    return configuration_done, []
            case ["continue" | "c"]:
                if debugger_state.already_running:
                    return dbg_continue, []
                else:
                    print("CMake build has not started running. Use 'run' command to start running")
            case ["variables" | "vars"]:
                if not debugger_state.already_running:
                    print(
                        "CMake build has not started running. Cannot print any variables yet. Use 'run' command to start running")
                    continue
                return stacktrace, []
            case ["get", "variable" | "var", varname]:
                debugger_state.single_variable = varname
                return stacktrace, []
            case ["quit" | "q"]:
                # TODO: we should probably change this to something that cleans up
                # the socket but this will do for now
                dbg_quit(debugger_state)
            case []:
                continue
            case _:
                print("Unknown command")


def print_help():
    print("Usage: cmakedebug cmake <options>")


def launch_cmake(cmd: list, pipe_host):

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
    debugger_state.cmake_process_handle = launch_cmake(sys.argv[1:], debugger_state.host)
    print(debugger_state.cmake_process_handle)

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
                    request_func, args = process_user_input(debugger_state)
                    send_request(s, request_func, *args)
                case {"type": "response", "command": "stackTrace",
                      "body": {"stackFrames": [{"id": frame_id}]}}:
                    send_request(s, scopes, frame_id)
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
                    if debugger_state.single_variable:
                        if debugger_state.single_variable in debugger_state.cmake_variables:
                            print(
                                f"{debugger_state.single_variable}={debugger_state.cmake_variables[debugger_state.single_variable]}")
                        else:
                            print(f"{debugger_state.single_variable} does not exist")
                        debugger_state.single_variable = ""
                    else:
                        pprint(debugger_state.cmake_variables)
                    request_func, args = process_user_input(debugger_state)
                    send_request(s, request_func, *args)

                case _:  # Default case if no other case is matched
                    # Consider logging this for debugging.
                    print(f"Unhandled message type: {body_json}")
                    pass


if __name__ == '__main__':
    main()
