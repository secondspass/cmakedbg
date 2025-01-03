from cmakedbg import cmakedbg
from pathlib import Path
import time
import shutil
import pytest
import socket
from subprocess import Popen
import json


def test_validate_filepath_and_linenum():
    vfl = cmakedbg.validate_filepath_and_linenum
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
    debugger_state = cmakedbg.DebuggerState()
    assert debugger_state.seq == 0
    assert len(debugger_state.host.split('-')) == 6
    assert "/tmp/cmake" in debugger_state.host
    assert debugger_state.already_running is False
    assert debugger_state.cmake_variables == {}
    assert debugger_state.top_level_vars == 0


def test_initialize():
    initi = cmakedbg.initialize()
    assert initi['command'] == 'initialize'


@pytest.fixture(scope='session')
def debugger_state(scope="session"):
    return cmakedbg.DebuggerState()


@pytest.fixture(scope='session')
def cmake_background_process(debugger_state):
    cmake_dir = Path("./tests/cmake-examples-master/08-mpi").resolve()
    build_dir = cmake_dir.joinpath("build").resolve()
    if build_dir.is_dir():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    with Popen(["cmake", "--debugger", f"--debugger-pipe {debugger_state.host}", ".."], cwd=build_dir) as bg_process:
        time.sleep(0.5)
        yield bg_process
        bg_process.kill()


@pytest.fixture(scope="session")
def cmake_dap_socket(debugger_state, cmake_background_process):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(debugger_state.host)
        yield s


def test_create_request():
    request_bytes = cmakedbg.create_request(cmakedbg.initialize())
    assert type(request_bytes) is bytes
    header, request = request_bytes.split(b"\r\n\r\n")
    content_length = header.decode().split()[-1]
    assert int(content_length) == len(request.decode())
    payload = json.loads(request.decode())
    assert payload['seq'] == 1
    assert payload['type'] == 'request'


def test_send_request(debugger_state, cmake_dap_socket):
    cmakedbg.send_request(cmake_dap_socket, cmakedbg.initialize)
    body_json, response = cmakedbg.recv_response(cmake_dap_socket, b"")
    assert body_json["type"] == "response"
    assert body_json["command"] == "initialize"
    body_json, response = cmakedbg.recv_response(cmake_dap_socket, response)
    assert (body_json["type"], body_json["event"]) == ("event", "initialized")
