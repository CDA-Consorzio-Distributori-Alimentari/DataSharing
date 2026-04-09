import ctypes
from ctypes import wintypes

class _SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Sid", wintypes.LPVOID),
        ("Attributes", wintypes.DWORD),
    ]

class _TOKEN_GROUPS(ctypes.Structure):
    _fields_ = [
        ("GroupCount", wintypes.DWORD),
        ("Groups", _SID_AND_ATTRIBUTES * 1),
    ]
