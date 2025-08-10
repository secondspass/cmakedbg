from cmakedbg import debugger
import os
from pprint import pprint
from pathlib import Path
import time
import shutil
import pytest
import socket
from subprocess import Popen
import json


def test_validate_filepath_and_linenum():
    vfl = debugger.validate_filepath_and_linenum
    filename = "./tests/cmake-examples-master/08-mpi/CMakeLists.txt"
    fullpath = str(Path(filename).expanduser().resolve())

    # improper format
    with pytest.raises(RuntimeWarning):
        vfl(f"{filename}:12:34")
    # fake line numbers
    for fakelinenumber in ["asdg", "13sgh"]:
        with pytest.raises(ValueError):
            vfl(f"{filename}:{fakelinenumber}")
    # non existent file
    with pytest.raises(RuntimeWarning):
        vfl("./sdfgdstyw34")
    assert (fullpath, 1) == vfl(f"{filename}")
    assert (fullpath, 23) == vfl(f"{filename}:23")


def test_debugger_state():
    debugger_state = debugger.DebuggerState()
    assert len(debugger_state.host.split('-')) == 6
    assert "/tmp/cmake" in debugger_state.host
    assert debugger_state.already_running is False
    assert debugger_state.cmake_variables == {}
    assert debugger_state.top_level_vars == 0


def test_initialize():
    initi = debugger.initialize()
    assert initi['command'] == 'initialize'


@pytest.fixture(scope='class')
def debugger_state():
    return debugger.DebuggerState()


@pytest.fixture(scope='class')
def cmake_background_process(debugger_state):
    cmake_dir = Path("./tests/cmake-examples-master/08-mpi").resolve()
    curr_dir = Path(".").resolve()
    build_dir = cmake_dir.joinpath("build").resolve()
    if build_dir.is_dir():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    os.chdir(str(build_dir))
    bg_process = debugger.launch_cmake(["cmake", ".."], debugger_state.host, lambda: print("help"))
    yield bg_process
    bg_process.kill()
    os.chdir(str(curr_dir))


@pytest.fixture(scope='class')
def cmake_dap_socket(debugger_state, cmake_background_process):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(debugger_state.host)
        yield s


def test_create_request():
    request_bytes = debugger.create_request(debugger.initialize())
    assert type(request_bytes) is bytes
    header, request = request_bytes.split(b"\r\n\r\n")
    content_length = header.decode().split()[-1]
    assert int(content_length) == len(request.decode())
    payload = json.loads(request.decode())
    assert payload['seq'] == 1
    assert payload['type'] == 'request'


def test_send_request(debugger_state, cmake_dap_socket, cmake_background_process):
    debugger_state.cmake_process_handle = cmake_background_process
    debugger.send_request(cmake_dap_socket, debugger.initialize)
    body_json, debugger_state.response = debugger.recv_response(cmake_dap_socket,
                                                                debugger_state.response)
    assert (body_json["type"], body_json["command"]) == ("response", "initialize")
    body_json, debugger_state.response = debugger.recv_response(
        cmake_dap_socket, debugger_state.response)
    assert (body_json["type"], body_json["event"]) == ("event", "initialized")


def test_process_user_input(debugger_state):
    # TODO: fill this out
    pass


def test_parse_command(debugger_state):
    pc = debugger.parse_command
    # TODO: fill this out
    # pipe command
    # TODO
    # breakpoint command:
    # case 1: good filepath
    filepath_and_linenum = "./tests/cmake-examples-master/08-mpi/CMakeLists.txt:2"
    filepath, linenum = debugger.validate_filepath_and_linenum(filepath_and_linenum)
    for cmdname in ["breakpoint", "break", "br"]:
        assert (debugger.set_breakpoints,
                [filepath, linenum]) == pc(debugger_state,
                                           [cmdname,
                                            filepath_and_linenum])
    # case 2: bad linenum
    filepath_and_linenum = "./tests/cmake-examples-master/08-mpi/CMakeLists.txt:5a0"
    for cmdname in ["breakpoint", "break", "br"]:
        assert "line number is not a valid integer" in pc(debugger_state,
                                                          [cmdname,
                                                           filepath_and_linenum]).getvalue()
    # case 3: bad filepath
    filepath_and_linenum = "./tests/casdfdsafmake-examples-master/08-mpi/CMakeLists.txt:50"
    for cmdname in ["breakpoint", "break", "br"]:
        assert "is not a valid file" in pc(debugger_state,
                                           [cmdname,
                                            filepath_and_linenum]).getvalue()
    # case 4: malformed input
    filepath_and_linenum = "./tests/cmake-examples-master/08-mpi/CMakeLists.txt:50:12"
    for cmdname in ["breakpoint", "break", "br"]:
        assert "breakpoint should be of the form" in pc(debugger_state,
                                                        [cmdname,
                                                         filepath_and_linenum]).getvalue()

    # run command:
    # case 1: already running
    # case 2: not already running


# each function executes in sequence
# TODO: add piece that will run these tests on different CMakeLists from the cmake example
# collection.
class TestCommands:
    def test_initialize(self, debugger_state, cmake_dap_socket, cmake_background_process):
        debugger_state.cmake_process_handle = cmake_background_process
        debugger.send_request(cmake_dap_socket, debugger.initialize)
        body_json, debugger_state.response = debugger.recv_response(cmake_dap_socket,
                                                                    debugger_state.response)
        assert (body_json["type"], body_json["command"]) == ("response", "initialize")
        body_json, debugger_state.response = debugger.recv_response(
            cmake_dap_socket, debugger_state.response)
        assert (body_json["type"], body_json["event"]) == ("event", "initialized")

    def test_set_breakpoints(self, debugger_state, cmake_dap_socket):
        filepath, linenum = debugger.validate_filepath_and_linenum("../CMakeLists.txt:6")
        debugger.send_request(cmake_dap_socket, debugger.set_breakpoints,
                              filepath, linenum)
        body_json, debugger_state.response = debugger.recv_response(cmake_dap_socket,
                                                                    debugger_state.response)
        assert (body_json["type"], body_json["command"]) == ("response", "setBreakpoints")

    def test_configuration_done(self, debugger_state, cmake_dap_socket):
        debugger.send_request(cmake_dap_socket, debugger.configuration_done)
        body_json, debugger_state.response = debugger.recv_response(
            cmake_dap_socket, debugger_state.response)
        assert (body_json["type"], body_json["command"]) == ("response", "configurationDone")

    def test_stop_at_first_breakpoint(self, debugger_state, cmake_dap_socket):
        body_json, debugger_state.response = debugger.recv_response(cmake_dap_socket,
                                                                    debugger_state.response)
        assert (body_json["type"],
                body_json["event"],
                body_json["body"]["reason"]) == ("event",
                                                 "thread",
                                                 "started")
        body_json, debugger_state.response = debugger.recv_response(
            cmake_dap_socket, debugger_state.response)
        assert (body_json["type"],
                body_json["event"],
                body_json["body"]["reason"],
                body_json["body"]["breakpoint"]["verified"]) == ("event", "breakpoint", "changed", True)
        body_json, debugger_state.response = debugger.recv_response(
            cmake_dap_socket, debugger_state.response)
        assert (body_json["type"],
                body_json["event"],
                body_json["body"]["reason"]) == ("event",
                                                 "stopped",
                                                 "breakpoint")

    def test_get_breakpoints(self, debugger_state, cmake_dap_socket):
        # cmake hasn't implemented the 'breakpointLocations' handler yet
        pass

    def test_get_variables(self, debugger_state, cmake_dap_socket):
        debugger.send_request(cmake_dap_socket, debugger.stacktrace)
        body_json, debugger_state.response = debugger.recv_response(cmake_dap_socket,
                                                                    debugger_state.response)
        assert (body_json["type"],
                body_json["command"],) == ("response", "stackTrace")
        assert isinstance(body_json["body"]["stackFrames"], list)

        # TODO: complete this

    def test_get_source(self, debugger_state, cmake_dap_socket):
        # TODO: complete this
        pass






