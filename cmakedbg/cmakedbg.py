import socket
import uuid
import sys
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
CMAKE_VARIABLES = {}
SINGLE_VARIABLE = None
TOP_LEVEL_VARS = 0


@dataclass
class DebugState():
    host: str = f"/tmp/cmake-{uuid.uuid4()}"
    seq: int = 0
    already_running: bool = False
    cmake_variables: dict = dataclasses.field(default_factory=dict)
    top_level_vars: int = 0




def send_request(s, request_func, *args):
    payload = request_func(*args)
    request_bytes = create_request(payload)

    # change this to log instead
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


def validate_filepath_and_linenum(filepath_and_linenum):
    filepathsplit = filepath_and_linenum.split(":")
    if len(filepathsplit) > 2:
        raise RuntimeWarning(
            "User error: breakpoint should be of the form '/path/to/file:linenumber'")
    if len(filepathsplit) == 2:
        try:
            filepath, linenum = filepathsplit[0], int(filepathsplit[1])
        except ValueError:
            raise ValueError(f"User error: line number is not a valid integer in {
                             filepath_and_linenum}")
    else:
        filepath, linenum = filepathsplit[0], 1
    filepath = pathlib.Path(filepath).expanduser().resolve()
    if filepath.is_file():
        return str(filepath), linenum
    else:
        raise RuntimeWarning(f"User error: {filepath} is not a valid file")


def dbg_quit():
    print()
    sys.exit(0)


def process_user_input():
    global ALREADY_RUNNING
    global SINGLE_VARIABLE
    while True:
        try:
            user_input = input(">>> ").strip().split()
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt")
            continue
        except EOFError:
            dbg_quit()

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
            case ["run" | "r"]:
                if ALREADY_RUNNING:
                    print("CMake already started running. Ignoring command.")
                else:
                    return configuration_done, []
            case ["continue" | "c"]:
                if ALREADY_RUNNING:
                    return dbg_continue, []
                else:
                    print("CMake not running. Use 'run' command to start running")
            case ["variables" | "vars"]:
                if not ALREADY_RUNNING:
                    print("CMake build is not running. Cannot print any variables")
                    continue
                return stacktrace, []
            case ["get", "variable" | "var", varname]:
                SINGLE_VARIABLE = varname
                return stacktrace, []
                pass
            case ["quit" | "q"]:
                # TODO: we should probably change this to something that cleans up
                # the socket but this will do for now
                dbg_quit()
            case []:
                continue
            case _:
                print("Unknown command")


def main():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(HOST)
        response = b""

        send_request(s, initialize)
        global CMAKE_VARIABLES
        global SINGLE_VARIABLE

        while True:
            body_json, response = recv_response(s, response)

            match body_json:
                case {"type": "response", "command": "initialize"}:
                    pass
                case {"type": "event", "event": "initialized"}:
                    request_func, args = process_user_input()
                    send_request(s, request_func, *args)
                case {"type": "response", "command": "setBreakpoints"}:
                    request_func, args = process_user_input()
                    send_request(s, request_func, *args)
                case {"type": "response", "command": "configurationDone"}:
                    global ALREADY_RUNNING
                    ALREADY_RUNNING = True
                    pass
                case {"type": "event", "event": "stopped"}:
                    request_func, args = process_user_input()
                    send_request(s, request_func, *args)
                case {"type": "response", "command": "stackTrace",
                      "body": {"stackFrames": [{"id": frame_id}]}}:
                    send_request(s, scopes, frame_id)
                case {"type": "response", "command": "scopes",
                      "body": {"scopes": [{"variablesReference": var_ref}]}}:
                    send_request(s, variables, var_ref)
                case {"type": "response", "command": "variables"}:
                    global TOP_LEVEL_VARS
                    for variable in body_json['body']['variables']:
                        CMAKE_VARIABLES[variable['name']] = variable['value']
                        if variable['name'] in ['CacheVariables', 'Directories', 'Locals']:
                            TOP_LEVEL_VARS = TOP_LEVEL_VARS + 1
                            send_request(s, variables, variable['variablesReference'])
                    if TOP_LEVEL_VARS > 0:
                        TOP_LEVEL_VARS = TOP_LEVEL_VARS - 1
                        continue
                    if SINGLE_VARIABLE is not None:
                        if SINGLE_VARIABLE in CMAKE_VARIABLES:
                            print(f"{SINGLE_VARIABLE} = {CMAKE_VARIABLES[SINGLE_VARIABLE]}")
                        else:
                            print(f"{SINGLE_VARIABLE} does not exist")
                        SINGLE_VARIABLE = None
                    else:
                        pprint(CMAKE_VARIABLES)
                    request_func, args = process_user_input()
                    send_request(s, request_func, *args)

                case _:  # Default case if no other case is matched
                    # Consider logging this for debugging.
                    print(f"Unhandled message type: {body_json}")
                    pass


if __name__ == '__main__':
    main()
