import binascii
from collections import abc, namedtuple
import copy
import itertools
import re
from typing import TYPE_CHECKING, Any, Callable, Collection, Coroutine, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Type, Union, cast
from eth_abi import codec, decoding, encoding
from eth_abi.base import parse_type_str
from eth_abi.exceptions import ValueOutOfBounds
from eth_abi.grammar import ABIType, BasicType, TupleType, parse
from eth_abi.registry import ABIRegistry, BaseEquals, registry as default_registry
from eth_typing import HexStr, TypeStr
from eth_utils import decode_hex, is_bytes, is_list_like, is_string, is_text, to_text, to_tuple
from eth_utils.abi import collapse_if_tuple
from eth_utils.toolz import curry, partial, pipe
from web3._utils.decorators import reject_recursive_repeats
from web3._utils.ens import is_ens_name
from web3._utils.formatters import recursive_map
from web3.exceptions import FallbackNotFound, MismatchedABI
from web3.types import ABI, ABIEvent, ABIEventParams, ABIFunction, ABIFunctionParams, TReturn
from web3.utils import get_abi_input_names
if TYPE_CHECKING:
    from web3 import AsyncWeb3

def get_normalized_abi_arg_type(abi_arg: ABIEventParams) -> str:
    """
    Return the normalized type for the abi argument provided.
    In order to account for tuple argument types, this abstraction
    makes use of `collapse_if_tuple()` to collapse the appropriate component
    types within a tuple type, if present.
    """
    return collapse_if_tuple(dict(abi_arg)["type"])

class AddressEncoder(encoding.AddressEncoder):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

class AcceptsHexStrEncoder(encoding.BaseEncoder):
    subencoder_cls: Type[encoding.BaseEncoder] = None
    is_strict: bool = None
    is_big_endian: bool = False
    data_byte_size: int = None
    value_bit_size: int = None

    def __init__(self, subencoder: encoding.BaseEncoder, **kwargs: Dict[str, Any]) -> None:
        super().__init__(**kwargs)
        self.subencoder = subencoder
        self.is_dynamic = subencoder.is_dynamic

class BytesEncoder(AcceptsHexStrEncoder):
    subencoder_cls = encoding.BytesEncoder
    is_strict = False

class ExactLengthBytesEncoder(BytesEncoder):
    is_strict = True

class ByteStringEncoder(AcceptsHexStrEncoder):
    subencoder_cls = encoding.ByteStringEncoder
    is_strict = False

class StrictByteStringEncoder(AcceptsHexStrEncoder):
    subencoder_cls = encoding.ByteStringEncoder
    is_strict = True

class TextStringEncoder(encoding.TextStringEncoder):
    pass

def merge_args_and_kwargs(function_abi: ABIFunction, args: Sequence[Any], kwargs: Dict[str, Any]) -> Tuple[Any, ...]:
    """
    Takes a list of positional args (``args``) and a dict of keyword args
    (``kwargs``) defining values to be passed to a call to the contract function
    described by ``function_abi``.  Checks to ensure that the correct number of
    args were given, no duplicate args were given, and no unknown args were
    given.  Returns a list of argument values aligned to the order of inputs
    defined in ``function_abi``.
    """
    if len(args) + len(kwargs) > len(function_abi.get('inputs', [])):
        raise TypeError(
            "Too many arguments: got {0} args and {1} kwargs, expected {2}".format(
                len(args), len(kwargs), len(function_abi.get('inputs', []))
            )
        )

    args_as_kwargs = {}
    for arg_name, arg_value in zip(get_abi_input_names(function_abi), args):
        args_as_kwargs[arg_name] = arg_value

    duplicate_args = set(args_as_kwargs).intersection(kwargs)
    if duplicate_args:
        raise TypeError(
            "Duplicate arguments: {0}".format(", ".join(duplicate_args))
        )

    unknown_args = set(kwargs).difference(get_abi_input_names(function_abi))
    if unknown_args:
        if function_abi.get('name'):
            raise TypeError(
                "Unknown arguments for function {0}: {1}".format(
                    function_abi.get('name'),
                    ", ".join(unknown_args),
                )
            )
        raise TypeError(
            "Unknown arguments: {0}".format(", ".join(unknown_args))
        )

    sorted_arg_names = [arg_abi['name'] for arg_abi in function_abi.get('inputs', [])]

    return tuple(
        kwargs.get(arg_name, args_as_kwargs.get(arg_name))
        for arg_name in sorted_arg_names
    )
TUPLE_TYPE_STR_RE = re.compile('^(tuple)((\\[([1-9]\\d*\\b)?])*)??$')

def get_tuple_type_str_parts(s: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Takes a JSON ABI type string.  For tuple type strings, returns the separated
    prefix and array dimension parts.  For all other strings, returns ``None``.
    """
    match = TUPLE_TYPE_STR_RE.match(s)
    if match is None:
        return None

    tuple_prefix = match.group(1)
    tuple_dims = match.group(2)

    return tuple_prefix, tuple_dims or None

def _align_abi_input(arg_abi: ABIFunctionParams, arg: Any) -> Tuple[Any, ...]:
    """
    Aligns the values of any mapping at any level of nesting in ``arg``
    according to the layout of the corresponding abi spec.
    """
    if isinstance(arg, (list, tuple)):
        if len(arg_abi['components']) != len(arg):
            raise ValueError(
                "Mismatched lengths between components and values. "
                f"Got {len(arg)} values and {len(arg_abi['components'])} components."
            )
        return tuple(
            _align_abi_input(component_abi, component)
            for component_abi, component
            in zip(arg_abi['components'], arg)
        )
    elif isinstance(arg, Mapping):
        return tuple(
            _align_abi_input(component_abi, arg.get(component_abi['name'], None))
            for component_abi in arg_abi['components']
        )
    else:
        return (arg,)

def get_aligned_abi_inputs(abi: ABIFunction, args: Union[Tuple[Any, ...], Mapping[Any, Any]]) -> Tuple[Tuple[Any, ...], Tuple[Any, ...]]:
    """
    Takes a function ABI (``abi``) and a sequence or mapping of args (``args``).
    Returns a list of type strings for the function's inputs and a list of
    arguments which have been aligned to the layout of those types.  The args
    contained in ``args`` may contain nested mappings or sequences corresponding
    to tuple-encoded values in ``abi``.
    """
    input_types = tuple(collapse_if_tuple(arg_abi) for arg_abi in abi.get('inputs', []))

    if isinstance(args, (list, tuple)):
        aligned_args = tuple(
            _align_abi_input(arg_abi, arg)
            for arg_abi, arg in zip(abi.get('inputs', []), args)
        )
    elif isinstance(args, Mapping):
        aligned_args = tuple(
            _align_abi_input(arg_abi, args.get(arg_abi['name'], None))
            for arg_abi in abi.get('inputs', [])
        )
    else:
        raise TypeError(f"Args must be a sequence or mapping, got {type(args)}")

    return input_types, aligned_args
DYNAMIC_TYPES = ['bytes', 'string']
INT_SIZES = range(8, 257, 8)
BYTES_SIZES = range(1, 33)
UINT_TYPES = [f'uint{i}' for i in INT_SIZES]
INT_TYPES = [f'int{i}' for i in INT_SIZES]
BYTES_TYPES = [f'bytes{i}' for i in BYTES_SIZES] + ['bytes32.byte']
STATIC_TYPES = list(itertools.chain(['address', 'bool'], UINT_TYPES, INT_TYPES, BYTES_TYPES))
BASE_TYPE_REGEX = '|'.join((_type + '(?![a-z0-9])' for _type in itertools.chain(STATIC_TYPES, DYNAMIC_TYPES)))
SUB_TYPE_REGEX = '\\[[0-9]*\\]'
TYPE_REGEX = '^(?:{base_type})(?:(?:{sub_type})*)?$'.format(base_type=BASE_TYPE_REGEX, sub_type=SUB_TYPE_REGEX)

def size_of_type(abi_type: TypeStr) -> int:
    """
    Returns size in bits of abi_type
    """
    if 'string' in abi_type:
        return None
    if 'byte' in abi_type:
        return None
    if '[' in abi_type:
        sub_type = abi_type[:abi_type.index('[')]
        return size_of_type(sub_type)
    if abi_type.startswith('uint') or abi_type.startswith('int'):
        return int(abi_type[4:])
    if abi_type == 'bool':
        return 8
    if abi_type == 'address':
        return 160
    raise ValueError(f"Unsupported ABI type: {abi_type}")
END_BRACKETS_OF_ARRAY_TYPE_REGEX = '\\[[^]]*\\]$'
ARRAY_REGEX = '^[a-zA-Z0-9_]+({sub_type})+$'.format(sub_type=SUB_TYPE_REGEX)
NAME_REGEX = '[a-zA-Z_][a-zA-Z0-9_]*'
ENUM_REGEX = '^{lib_name}\\.{enum_name}$'.format(lib_name=NAME_REGEX, enum_name=NAME_REGEX)

@curry
def map_abi_data(normalizers: Sequence[Callable[[TypeStr, Any], Tuple[TypeStr, Any]]], types: Sequence[TypeStr], data: Sequence[Any]) -> Any:
    """
    This function will apply normalizers to your data, in the
    context of the relevant types. Each normalizer is in the format:

    def normalizer(datatype, data):
        # Conditionally modify data
        return (datatype, data)

    Where datatype is a valid ABI type string, like "uint".

    In case of an array, like "bool[2]", normalizer will receive `data`
    as an iterable of typed data, like `[("bool", True), ("bool", False)]`.

    Internals
    ---

    This is accomplished by:

    1. Decorating the data tree with types
    2. Recursively mapping each of the normalizers to the data
    3. Stripping the types back out of the tree
    """
    pipeline = itertools.chain(
        [abi_data_tree(types)],
        map(data_tree_map, normalizers),
        [partial(recursive_map, strip_abi_type)],
    )

    return pipe(data, *pipeline)

@curry
def abi_data_tree(types: Sequence[TypeStr], data: Sequence[Any]) -> List[Any]:
    """
    Decorate the data tree with pairs of (type, data). The pair tuple is actually an
    ABITypedData, but can be accessed as a tuple.

    As an example:

    >>> abi_data_tree(types=["bool[2]", "uint"], data=[[True, False], 0])
    [("bool[2]", [("bool", True), ("bool", False)]), ("uint256", 0)]
    """
    return [
        abi_sub_tree(type_str, data_value)
        for type_str, data_value
        in zip(types, data)
    ]

def abi_sub_tree(type_str: TypeStr, data_value: Any) -> ABITypedData:
    if is_array_type(type_str):
        item_type_str = re.match(r'([a-z0-9_]+)(?:\[.*\])+$', type_str).group(1)
        return ABITypedData([
            type_str,
            [abi_sub_tree(item_type_str, sub_value) for sub_value in data_value]
        ])
    else:
        return ABITypedData([type_str, data_value])

@curry
def data_tree_map(func: Callable[[TypeStr, Any], Tuple[TypeStr, Any]], data_tree: Any) -> 'ABITypedData':
    """
    Map func to every ABITypedData element in the tree. func will
    receive two args: abi_type, and data
    """
    def map_to_typed_data(elements: Iterable[Any]) -> List['ABITypedData']:
        return [
            ABITypedData(func(*value))
            if isinstance(value, ABITypedData)
            else data_tree_map(func, value)
            for value in elements
        ]

    if isinstance(data_tree, ABITypedData):
        return ABITypedData(func(*data_tree))
    elif is_list_like(data_tree):
        return map_to_typed_data(data_tree)
    else:
        return data_tree

class ABITypedData(namedtuple('ABITypedData', 'abi_type, data')):
    """
    This class marks data as having a certain ABI-type.

    >>> a1 = ABITypedData(['address', addr1])
    >>> a2 = ABITypedData(['address', addr2])
    >>> addrs = ABITypedData(['address[]', [a1, a2]])

    You can access the fields using tuple() interface, or with
    attributes:

    >>> assert a1.abi_type == a1[0]
    >>> assert a1.data == a1[1]

    Unlike a typical `namedtuple`, you initialize with a single
    positional argument that is iterable, to match the init
    interface of all other relevant collections.
    """

    def __new__(cls, iterable: Iterable[Any]) -> 'ABITypedData':
        return super().__new__(cls, *iterable)

def named_tree(abi: Iterable[Union[ABIFunctionParams, ABIFunction, ABIEvent, Dict[TypeStr, Any]]], data: Iterable[Tuple[Any, ...]]) -> Dict[str, Any]:
    """
    Convert function inputs/outputs or event data tuple to dict with names from ABI.
    """
    result = {}
    for param, value in zip(abi, data):
        if isinstance(param, Mapping):
            param_name = param['name']
            if param_name:
                if 'components' in param:
                    result[param_name] = named_tree(param['components'], value)
                else:
                    result[param_name] = value
        elif is_list_like(param):
            result.update(named_tree(param, value))
    return result

async def async_data_tree_map(async_w3: 'AsyncWeb3', func: Callable[['AsyncWeb3', TypeStr, Any], Coroutine[Any, Any, Tuple[TypeStr, Any]]], data_tree: Any) -> 'ABITypedData':
    """
    Map an awaitable method to every ABITypedData element in the tree.

    The awaitable method should receive three positional args:
        async_w3, abi_type, and data
    """
    async def async_map_to_typed_data(elements: Iterable[Any]) -> List['ABITypedData']:
        return [
            ABITypedData(await func(async_w3, *value))
            if isinstance(value, ABITypedData)
            else await async_data_tree_map(async_w3, func, value)
            for value in elements
        ]

    if isinstance(data_tree, ABITypedData):
        return ABITypedData(await func(async_w3, *data_tree))
    elif is_list_like(data_tree):
        return await async_map_to_typed_data(data_tree)
    else:
        return data_tree

@reject_recursive_repeats
async def async_recursive_map(async_w3: 'AsyncWeb3', func: Callable[[Any], Coroutine[Any, Any, TReturn]], data: Any) -> TReturn:
    """
    Apply an awaitable method to data and any collection items inside data
    (using async_map_collection).

    Define the awaitable method so that it only applies to the type of value that you
    want it to apply to.
    """
    async def recurse(item: Any) -> Any:
        return await async_recursive_map(async_w3, func, item)

    items = await async_map_if_collection(recurse, data)
    return await func(items)

async def async_map_if_collection(func: Callable[[Any], Coroutine[Any, Any, Any]], value: Any) -> Any:
    """
    Apply an awaitable method to each element of a collection or value of a dictionary.
    If the value is not a collection, return it unmodified.
    """
    if isinstance(value, Mapping):
        return {
            key: await func(val)
            for key, val in value.items()
        }
    elif is_list_like(value):
        return [await func(item) for item in value]
    else:
        return value
