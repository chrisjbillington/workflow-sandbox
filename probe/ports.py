#####################################################################
#                                                                   #
# /ports.py                                                         #
#                                                                   #
# Copyright 2026, Monash University and contributors                #
#                                                                   #
# This file is part of the labscript_utils, in the labscript suite  #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import socket
import sys

if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    # From mstcpip.h
    SIO_TCP_INITIAL_RTO = 0x98000011
    TCP_INITIAL_RTO_UNSPECIFIED_RTT = 0xFFFF
    TCP_INITIAL_RTO_NO_SYN_RETRANSMISSIONS = 0xFE

    class TCP_INITIAL_RTO_PARAMETERS(ctypes.Structure):
        _fields_ = [('Rtt', wintypes.USHORT), ('MaxSynRetransmissions', ctypes.c_ubyte)]

    _ws2_32 = ctypes.WinDLL('ws2_32', use_last_error=True)
    _WSAIoctl = _ws2_32.WSAIoctl
    _WSAIoctl.argtypes = [
        ctypes.c_size_t,  # SOCKET
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    _WSAIoctl.restype = ctypes.c_int

    def _disable_syn_retransmissions(sock):
        """Make a connection attempt on the socket fail as soon as it is refused. By
        default Windows retransmits the SYN after a refusal, so that a connection to a
        port with no listener fails only after about a second."""
        params = TCP_INITIAL_RTO_PARAMETERS(
            TCP_INITIAL_RTO_UNSPECIFIED_RTT, TCP_INITIAL_RTO_NO_SYN_RETRANSMISSIONS
        )
        returned = wintypes.DWORD()
        result = _WSAIoctl(
            sock.fileno(),
            SIO_TCP_INITIAL_RTO,
            ctypes.byref(params),
            ctypes.sizeof(params),
            None,
            0,
            ctypes.byref(returned),
            None,
            None,
        )
        if result != 0:
            raise ctypes.WinError(ctypes.get_last_error())


def port_in_use(port, timeout=1):
    """Return whether a process on this computer is listening on the TCP port, by
    attempting a connection to it on 127.0.0.1 and closing the connection without
    sending anything. A connection attempt that times out after `timeout` seconds means
    that a process is listening but not accepting connections, and returns True."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sys.platform == 'win32':
            _disable_syn_retransmissions(sock)
        sock.settimeout(timeout)
        try:
            sock.connect(('127.0.0.1', port))
        except ConnectionRefusedError:
            return False
        except TimeoutError:
            return True
        return True
