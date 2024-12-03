import codecs
import functools
import json
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, Union, cast
from eth_abi.exceptions import ParseError
from eth_abi.grammar import BasicType, parse
from eth_typing import ChecksumAddress, HexStr, TypeStr
from eth_utils import to_bytes, to_checksum_address, to_hex, to_text
from eth_utils.address import is_binary_address
from eth_utils.toolz import curry
from hexbytes import HexBytes
from ens import ENS, AsyncENS
from web3._utils.encoding import hexstr_if_str, text_if_str
from web3._utils.ens import StaticENS, async_validate_name_has_address, is_ens_name, validate_name_has_address
from web3._utils.validation import validate_abi, validate_address
from web3.exceptions import InvalidAddress, NameNotFound
from web3.types import ABI
if TYPE_CHECKING:
    from web3 import AsyncWeb3, Web3

def parse_basic_type_str(old_normalizer: Callable[[BasicType, TypeStr, Any], Tuple[TypeStr, Any]]) -> Callable[[TypeStr, Any], Tuple[TypeStr, Any]]:
    """
    Modifies a normalizer to automatically parse the incoming type string.  If
    that type string does not represent a basic type (i.e. non-tuple type) or is
    not parsable, the normalizer does nothing.
    """
    @functools.wraps(old_normalizer)
    def new_normalizer(type_str: TypeStr, value: Any) -> Tuple[TypeStr, Any]:
        try:
            abi_type = parse(type_str)
            if isinstance(abi_type, BasicType):
                return old_normalizer(abi_type, type_str, value)
        except ParseError:
            pass
        return type_str, value
    return new_normalizer
BASE_RETURN_NORMALIZERS = [addresses_checksummed]
