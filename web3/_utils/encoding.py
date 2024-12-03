import json
import re
from typing import Any, Callable, Dict, Iterable, Optional, Sequence, Type, Union
from eth_abi.encoding import BaseArrayEncoder
from eth_typing import HexStr, Primitives, TypeStr
from eth_utils import add_0x_prefix, encode_hex, is_bytes, is_hex, is_list_like, remove_0x_prefix, to_bytes, to_hex
from eth_utils.toolz import curry
from hexbytes import HexBytes
from web3._utils.abi import is_address_type, is_array_type, is_bool_type, is_bytes_type, is_int_type, is_string_type, is_uint_type, size_of_type, sub_type_of_array_type
from web3._utils.validation import validate_abi_type, validate_abi_value
from web3.datastructures import AttributeDict

def hex_encode_abi_type(abi_type: TypeStr, value: Any, force_size: Optional[int]=None) -> HexStr:
    """
    Encodes value into a hex string in format of abi_type
    """
    validate_abi_type(abi_type)
    validate_abi_value(abi_type, value)

    if abi_type.startswith("uint"):
        return to_hex_with_size(value, force_size or int(abi_type[4:]))
    elif abi_type.startswith("int"):
        return to_hex_twos_compliment(value, force_size or int(abi_type[3:]))
    elif abi_type == "address":
        return add_0x_prefix(pad_hex(remove_0x_prefix(value), 40))
    elif abi_type == "bool":
        return "0x01" if value else "0x00"
    elif abi_type.startswith("bytes"):
        if abi_type == "bytes":
            return add_0x_prefix(encode_hex(value))
        else:
            size = int(abi_type[5:])
            return add_0x_prefix(encode_hex(value).rjust(size * 2, '0'))
    elif abi_type == "string":
        return add_0x_prefix(encode_hex(value.encode('utf-8')))
    else:
        raise ValueError(f"Unsupported ABI type: {abi_type}")

def to_hex_twos_compliment(value: Any, bit_size: int) -> HexStr:
    """
    Converts integer value to twos compliment hex representation with given bit_size
    """
    if value >= 0:
        return to_hex_with_size(value, bit_size)
    else:
        return to_hex_with_size((1 << bit_size) + value, bit_size)

def to_hex_with_size(value: Any, bit_size: int) -> HexStr:
    """
    Converts a value to hex with given bit_size:
    """
    if isinstance(value, str):
        value = int(value, 16)
    if isinstance(value, int):
        hex_value = hex(value)[2:]
        return add_0x_prefix(pad_hex(hex_value, bit_size // 4))
    else:
        raise TypeError(f"Cannot convert {type(value)} to hex")

def pad_hex(value: Any, bit_size: int) -> HexStr:
    """
    Pads a hex string up to the given bit_size
    """
    value = remove_0x_prefix(value)
    return value.zfill(bit_size // 4)
zpad_bytes = pad_bytes(b'\x00')

@curry
def text_if_str(to_type: Callable[..., str], text_or_primitive: Union[Primitives, HexStr, str]) -> str:
    """
    Convert to a type, assuming that strings can be only unicode text (not a hexstr)

    @param to_type is a function that takes the arguments (primitive, hexstr=hexstr,
        text=text), eg~ to_bytes, to_text, to_hex, to_int, etc
    @param text_or_primitive in bytes, str, or int.
    """
    if isinstance(text_or_primitive, str):
        return to_type(text=text_or_primitive)
    else:
        return to_type(text_or_primitive)

@curry
def hexstr_if_str(to_type: Callable[..., HexStr], hexstr_or_primitive: Union[Primitives, HexStr, str]) -> HexStr:
    """
    Convert to a type, assuming that strings can be only hexstr (not unicode text)

    @param to_type is a function that takes the arguments (primitive, hexstr=hexstr,
        text=text), eg~ to_bytes, to_text, to_hex, to_int, etc
    @param hexstr_or_primitive in bytes, str, or int.
    """
    if isinstance(hexstr_or_primitive, str):
        return to_type(hexstr=hexstr_or_primitive)
    else:
        return to_type(hexstr_or_primitive)

class FriendlyJsonSerde:
    """
    Friendly JSON serializer & deserializer

    When encoding or decoding fails, this class collects
    information on which fields failed, to show more
    helpful information in the raised error messages.
    """

class DynamicArrayPackedEncoder(BaseArrayEncoder):
    is_dynamic = True

class Web3JsonEncoder(json.JSONEncoder):
    pass

def to_json(obj: Dict[Any, Any]) -> str:
    """
    Convert a complex object (like a transaction object) to a JSON string
    """
    return json.dumps(obj, cls=Web3JsonEncoder)
