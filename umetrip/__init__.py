# clang -shared -undefined dynamic_lookup -o libumetrip.so UMETrip.c
# clang -shared -fPIC -o libumetrip.so UMETrip.c


import ctypes
import os.path


__dir__ = os.path.dirname(__file__)

library_path = os.path.join(__dir__, "libumetrip.so")

libumetrip = ctypes.cdll.LoadLibrary(library_path)

def sign(s):
    if isinstance(s, str):
        s = s.encode('utf8')
    to = ctypes.create_string_buffer(12)
    origin = ctypes.create_string_buffer(s)

    libumetrip.UMETripSign(to, origin)
    return to.value


if __name__ == '__main__':
    tm = b'2019-06-26'
    res = umetrip_sign(tm + b'QW9850' + b'2019-06-26')
    print(res)
    res = umetrip_sign(tm + b'QW9850' + tm + b'2019-06-26')
    print(res)
    res = umetrip_sign(tm + b'QW9850' + tm + b'2019-06-26' + tm)
    print(res)
