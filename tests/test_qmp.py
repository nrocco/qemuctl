import pytest

from qemu.qmp import Qmp
from unittest.mock import patch


@patch("socket.socket")
def test_qmp_not_available(mock_socket):
    qmp = Qmp("fuubar.sock")
    assert isinstance(qmp, Qmp)
    assert qmp.path == "fuubar.sock"
    assert not qmp.socket
    assert qmp.events == []
    with pytest.raises(RuntimeError, match="Qmp monitor not available"):
        qmp.open()
    qmp.close()
    qmp.close()


@patch("os.read")
@patch("socket.socket")
def test_qmp_available(mock_socket, mock_read):
    mock_read.side_effect = (
        b'{"QMP":{"version":{"qemu":{"micro":0,"minor":6,"major":1},"package":""},"capabilities":[]}}',
        b'{"return":{}}',
    )
    with Qmp("fuubar.sock") as qmp:
        assert qmp.socket
        assert qmp.events == []
    assert not qmp.socket
    assert qmp.events == []


@patch("binascii.b2a_hex")
@patch("os.read")
@patch("socket.socket")
def test_qmp_query_status(mock_socket, mock_read, mock_b2a_hex):
    mock_b2a_hex.return_value = b"182912"
    mock_read.side_effect = (
        b'{"QMP":{"version":{"qemu":{"micro":0,"minor":6,"major":1},"package":""},"capabilities":[]}}',
        b'{"return":{}}',
        b'{"event":"BLOCK_IO_ERROR","data":{"device":"ide0-hd1"},"timestamp":{"seconds":1265044230,"microseconds":450486}}\n{"id":"182912","return":{"status":"running","singlestep":false,"running":true}}',
    )
    with Qmp("fuubar.sock") as qmp:
        status = qmp.execute("query-status")
        assert len(qmp.events) == 1
        assert qmp.events[0]['event'] == 'BLOCK_IO_ERROR'
        assert qmp.events[0]['data']['device'] == 'ide0-hd1'
    assert status["status"] == "running"
    assert 'id' not in status
    assert not qmp.socket
    assert qmp.events == []


@patch("binascii.b2a_hex")
@patch("os.read")
@patch("socket.socket")
def test_qmp_error(mock_socket, mock_read, mock_b2a_hex):
    mock_b2a_hex.return_value = b"182912"
    mock_read.side_effect = (
        b'{"QMP":{"version":{"qemu":{"micro":0,"minor":6,"major":1},"package":""},"capabilities":[]}}',
        b'{"return":{}}',
        b'{"error":{"desc":"Something went wrong"}}',
    )
    with pytest.raises(RuntimeError, match="Something went wrong"):
        qmp = Qmp("fuubar.sock")
        qmp.execute("query-status")
    assert qmp.socket
    qmp.close()
    assert not qmp.socket
