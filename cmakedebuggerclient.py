import socket
import json
import time
from pprint import pprint
HOST = "/tmp/cmake-blah"
SEQ = 0
BRKPTNUM = 0


def initialize():
    payload = {
        "command": 'initialize',
        'arguments': {
            'adapterID': "blah",
            'clientID': 'vimspector',
            'clientName': 'vimspector',
            'linesStartAt1': True,
            'columnsStartAt1': True,
            'locale': 'en_GB',
            'pathFormat': 'path',
        }
    }
    return payload


def set_breakpoints():
    payload = {
        'command': 'setBreakpoints',
        'arguments': {
            'source': {
                'name': 'main CMakeLists.txt',
                'path': '/lustre/orion/stf007/scratch/subil/inbox/olcf20750/samplebugproject/CMakeLists.txt'
            },
            'breakpoints': [
                {'line': 5},
                {'line': 7},
                {'line': 9},
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


with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    s.connect(HOST)

    payload = initialize()
    request_bytes = create_request(payload)

    print(request_bytes)
    s.sendall(request_bytes)

    response = b""
    response = response + s.recv(4096)
    while True:
        header, response = response.split(b"\r\n\r\n", maxsplit=1)
        header = header.decode()
        size = int(header.split()[1])  # geting content lenght value
        while len(response) < size:
            response = response + s.recv(4096)
        body, response = response[:size], response[size:]
        body_json = json.loads(body.decode())
        print(header)
        pprint(body_json)
        print("Length: ", len(body))
        print("", flush=True)

        if body_json['type'] == 'response' and body_json['command'] == 'initialize':
            pass
        elif body_json['type'] == 'event' and body_json['event'] == 'initialized':
            # send breakpoints request
            payload = set_breakpoints()
            request_bytes = create_request(payload)
            print(request_bytes)
            s.sendall(request_bytes)
            pass
        elif body_json['type'] == 'response' and body_json['command'] == 'setBreakpoints':
            payload = configuration_done()
            request_bytes = create_request(payload)
            print(request_bytes)
            s.sendall(request_bytes)
        elif body_json['type'] == 'response' and body_json['command'] == 'configurationDone':
            pass
        elif body_json['type'] == 'event' and body_json['event'] == 'stopped':
            BRKPTNUM = BRKPTNUM + 1
            payload = stacktrace()
            request_bytes = create_request(payload)
            print(request_bytes)
            s.sendall(request_bytes)
        elif body_json['type'] == 'response' and body_json['command'] == 'stackTrace':
            payload = scopes(body_json['body']['stackFrames'][0]['id'])
            request_bytes = create_request(payload)
            print(request_bytes)
            s.sendall(request_bytes)
        elif body_json['type'] == 'response' and body_json['command'] == 'scopes':
            payload = variables(body_json['body']['scopes'][0]['variablesReference'])
            request_bytes = create_request(payload)
            print(request_bytes)
            s.sendall(request_bytes)
        elif body_json['type'] == 'response' and body_json['command'] == 'variables':
            toprint = []
            for variable in body_json['body']['variables']:
                toprint.append(f"{variable['name']} = {variable['value']}\n")
                if variable['name'] in ['CacheVariables', 'Directories', 'Locals']:
                    payload = variables(variable['variablesReference'])
                    request_bytes = create_request(payload)
                    print(request_bytes)
                    s.sendall(request_bytes)
                    print(f"Requesting variables: {variable['name']}")
                    next_br = input("Next breakpoint? (y or n): ")
                    if next_br == 'y':
                        payload = dbg_continue()
                        request_bytes = create_request(payload)
                        print(request_bytes)
                        s.sendall(request_bytes)

            with open(f"variables_break{BRKPTNUM}.txt", 'a') as varfile:
                varfile.writelines(toprint)

        else:
            pass

        if len(response) == 0 or b"\r\n\r\n" not in response:
            response = response + s.recv(4096)
            continue
        else:
            continue
