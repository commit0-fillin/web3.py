import itertools
from typing import Any, Dict
from eth_typing import HexStr, TypeStr
from eth_utils import function_abi_to_4byte_selector, is_0x_prefixed, is_binary_address, is_boolean, is_bytes, is_checksum_address, is_dict, is_hex_address, is_integer, is_list_like, is_string, is_checksum_address
from eth_utils.curried import apply_formatter_to_array
from eth_utils.hexadecimal import encode_hex
from eth_utils.toolz import compose, groupby, valfilter, valmap
from ens.utils import is_valid_ens_name
from web3._utils.abi import abi_to_signature, filter_by_type, is_address_type, is_array_type, is_bool_type, is_bytes_type, is_int_type, is_recognized_type, is_string_type, is_uint_type, length_of_array_type, sub_type_of_array_type
from web3.exceptions import InvalidAddress
from web3.types import ABI, ABIFunction

def validate_abi(abi: ABI) -> None:
    """
    Helper function for validating an ABI
    """
    if not isinstance(abi, list):
        raise ValueError("ABI must be a list")
    
    for item in abi:
        if not isinstance(item, dict):
            raise ValueError("ABI items must be dictionaries")
        
        if "type" not in item:
            raise ValueError("ABI item must have a 'type' key")
        
        if item["type"] not in ["function", "event", "constructor", "fallback", "receive"]:
            raise ValueError(f"Invalid ABI item type: {item['type']}")
        
        if item["type"] in ["function", "event"]:
            if "name" not in item:
                raise ValueError(f"{item['type']} must have a 'name' key")
            
            if "inputs" not in item:
                raise ValueError(f"{item['type']} must have an 'inputs' key")
            
            if not isinstance(item["inputs"], list):
                raise ValueError(f"{item['type']} inputs must be a list")
            
            for input_item in item["inputs"]:
                if not isinstance(input_item, dict) or "type" not in input_item:
                    raise ValueError(f"{item['type']} input items must be dictionaries with a 'type' key")
        
        if item["type"] == "function":
            if "outputs" not in item:
                raise ValueError("Function must have an 'outputs' key")
            
            if not isinstance(item["outputs"], list):
                raise ValueError("Function outputs must be a list")
            
            for output_item in item["outputs"]:
                if not isinstance(output_item, dict) or "type" not in output_item:
                    raise ValueError("Function output items must be dictionaries with a 'type' key")

def validate_abi_type(abi_type: TypeStr) -> None:
    """
    Helper function for validating an abi_type
    """
    if not isinstance(abi_type, str):
        raise ValueError("ABI type must be a string")
    
    # Check for basic types
    basic_types = ["uint", "int", "address", "bool", "string", "bytes"]
    if any(abi_type.startswith(t) for t in basic_types):
        if abi_type.startswith(("uint", "int")):
            # Check for valid integer sizes
            size = abi_type[4:]
            if size and (not size.isdigit() or int(size) % 8 != 0 or int(size) > 256):
                raise ValueError(f"Invalid integer size in ABI type: {abi_type}")
        elif abi_type.startswith("bytes"):
            # Check for valid fixed-size bytes
            size = abi_type[5:]
            if size and (not size.isdigit() or int(size) == 0 or int(size) > 32):
                raise ValueError(f"Invalid bytes size in ABI type: {abi_type}")
        return
    
    # Check for array types
    if abi_type.endswith("]"):
        base_type, array_part = abi_type.rsplit("[", 1)
        validate_abi_type(base_type)
        if array_part != "]" and not array_part[:-1].isdigit():
            raise ValueError(f"Invalid array size in ABI type: {abi_type}")
        return
    
    # Check for tuple types
    if abi_type.startswith("tuple"):
        if not (abi_type == "tuple" or abi_type.startswith("tuple[")):
            raise ValueError(f"Invalid tuple type in ABI type: {abi_type}")
        return
    
    raise ValueError(f"Invalid ABI type: {abi_type}")

def validate_abi_value(abi_type: TypeStr, value: Any) -> None:
    """
    Helper function for validating a value against the expected abi_type
    Note: abi_type 'bytes' must either be python3 'bytes' object or ''
    """
    if abi_type.startswith(("uint", "int")):
        if not isinstance(value, int):
            raise ValueError(f"Expected int for {abi_type}, got {type(value)}")
        bits = int(abi_type[4:]) if len(abi_type) > 3 else 256
        if abi_type.startswith("uint"):
            if value < 0 or value >= 2**bits:
                raise ValueError(f"Value out of range for {abi_type}: {value}")
        else:
            if value < -2**(bits-1) or value >= 2**(bits-1):
                raise ValueError(f"Value out of range for {abi_type}: {value}")
    elif abi_type == "address":
        if not isinstance(value, str) or not value.startswith("0x") or len(value) != 42:
            raise ValueError(f"Invalid Ethereum address: {value}")
    elif abi_type == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"Expected bool, got {type(value)}")
    elif abi_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value)}")
    elif abi_type == "bytes":
        if not (isinstance(value, bytes) or value == ''):
            raise ValueError(f"Expected bytes or '', got {type(value)}")
    elif abi_type.startswith("bytes"):
        if not isinstance(value, bytes):
            raise ValueError(f"Expected bytes for {abi_type}, got {type(value)}")
        size = int(abi_type[5:])
        if len(value) != size:
            raise ValueError(f"Expected {size} bytes for {abi_type}, got {len(value)}")
    elif abi_type.endswith("]"):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"Expected list or tuple for {abi_type}, got {type(value)}")
        base_type, array_part = abi_type.rsplit("[", 1)
        if array_part != "]":
            size = int(array_part[:-1])
            if len(value) != size:
                raise ValueError(f"Expected {size} items for {abi_type}, got {len(value)}")
        for item in value:
            validate_abi_value(base_type, item)
    else:
        raise ValueError(f"Unsupported ABI type: {abi_type}")

def validate_address(value: Any) -> None:
    """
    Helper function for validating an address
    """
    if not isinstance(value, str):
        raise TypeError("Address must be a string")

    if not value.startswith("0x"):
        raise ValueError("Address must start with '0x'")

    if len(value) != 42:
        raise ValueError("Address must be 42 characters long")

    try:
        int(value[2:], 16)
    except ValueError:
        raise ValueError("Address must be a valid hexadecimal string")

    if not is_checksum_address(value):
        raise ValueError("Address must be a valid checksum address")
