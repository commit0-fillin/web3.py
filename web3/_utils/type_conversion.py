from typing import Union
from eth_typing import HexStr
from eth_utils import to_bytes, to_hex

def to_hex_if_bytes(val: Union[HexStr, str, bytes, bytearray]) -> HexStr:
    """
    Note: This method does not validate against all cases and is only
    meant to work with bytes and hex strings.
    """
    if isinstance(val, (bytes, bytearray)):
        return to_hex(val)
    return HexStr(val)

def to_bytes_if_hex(val: Union[HexStr, str, bytes, bytearray]) -> bytes:
    """
    Note: This method does not validate against all cases and is only
    meant to work with bytes and hex strings.
    """
    if isinstance(val, (str, HexStr)) and val.startswith(('0x', '0X')):
        return to_bytes(hexstr=val)
    return to_bytes(val)
