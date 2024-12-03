from abc import ABC, abstractmethod
from enum import Enum
import itertools
from typing import TYPE_CHECKING, Any, Collection, Dict, Iterable, List, Optional, Sequence, Tuple, Union, cast
from eth_abi import grammar
from eth_abi.codec import ABICodec
from eth_typing import ChecksumAddress, HexStr, Primitives, TypeStr
from eth_utils import encode_hex, event_abi_to_log_topic, is_list_like, keccak, to_bytes, to_dict, to_hex, to_tuple
from eth_utils.curried import apply_formatter_if
from eth_utils.toolz import complement, compose, cons, curry, valfilter
import web3
from web3._utils.abi import exclude_indexed_event_inputs, get_indexed_event_inputs, get_normalized_abi_arg_type, map_abi_data, named_tree, normalize_event_input_types
from web3._utils.encoding import encode_single_packed, hexstr_if_str
from web3._utils.normalizers import BASE_RETURN_NORMALIZERS
from web3.datastructures import AttributeDict
from web3.exceptions import InvalidEventABI, LogTopicError, MismatchedABI
from web3.types import ABIEvent, ABIEventParams, BlockIdentifier, EventData, FilterParams, LogReceipt
from web3.utils import get_abi_input_names
if TYPE_CHECKING:
    from web3 import AsyncWeb3, Web3
    from web3._utils.filters import AsyncLogFilter, LogFilter

@to_tuple
def get_event_abi_types_for_decoding(event_inputs: Sequence[ABIEventParams]) -> Iterable[TypeStr]:
    """
    Event logs use the `keccak(value)` for indexed inputs of type `bytes` or
    `string`.  Because of this we need to modify the types so that we can
    decode the log entries using the correct types.
    """
    for input_abi in event_inputs:
        if input_abi['indexed'] and input_abi['type'] in ('string', 'bytes'):
            yield 'bytes32'
        else:
            yield input_abi['type']

@curry
def get_event_data(abi_codec: ABICodec, event_abi: ABIEvent, log_entry: LogReceipt) -> EventData:
    """
    Given an event ABI and a log entry for that event, return the decoded
    event data
    """
    log_topics = log_entry['topics']
    log_data = log_entry['data']
    
    # Validate that the first log topic matches the event signature
    if event_abi_to_log_topic(event_abi) != log_topics[0]:
        raise LogTopicError("Event signature mismatch")
    
    indexed_inputs = get_indexed_event_inputs(event_abi)
    non_indexed_inputs = exclude_indexed_event_inputs(event_abi)
    
    # Decode indexed inputs
    decoded_indexed_data = abi_codec.decode_abi(
        [param['type'] for param in indexed_inputs],
        b''.join([HexBytes(log_topics[i + 1]) for i in range(len(indexed_inputs))])
    )
    
    # Decode non-indexed inputs
    decoded_non_indexed_data = abi_codec.decode_abi(
        [param['type'] for param in non_indexed_inputs],
        HexBytes(log_data)
    )
    
    # Combine decoded data
    decoded_data = concat_abi_arrays(decoded_indexed_data, decoded_non_indexed_data)
    
    # Create event_data dictionary
    event_data = {
        'args': AttributeDict(dict(zip(get_abi_input_names(event_abi), decoded_data))),
        'event': event_abi['name'],
        'logIndex': log_entry['logIndex'],
        'transactionIndex': log_entry['transactionIndex'],
        'transactionHash': log_entry['transactionHash'],
        'address': log_entry['address'],
        'blockHash': log_entry['blockHash'],
        'blockNumber': log_entry['blockNumber'],
    }
    
    return cast(EventData, AttributeDict(event_data))
normalize_topic_list = compose(remove_trailing_from_seq(remove_value=None), pop_singlets)
is_not_indexed = complement(is_indexed)

class BaseEventFilterBuilder:
    formatter = None
    _fromBlock = None
    _toBlock = None
    _address = None
    _immutable = False

    def __init__(self, event_abi: ABIEvent, abi_codec: ABICodec, formatter: Optional[EventData]=None) -> None:
        self.event_abi = event_abi
        self.abi_codec = abi_codec
        self.formatter = formatter
        self.event_topic = event_abi_to_log_topic(self.event_abi)
        self.args = AttributeDict(_build_argument_filters_from_event_abi(event_abi, abi_codec))
        self._ordered_arg_names = tuple(arg['name'] for arg in event_abi['inputs'])

class EventFilterBuilder(BaseEventFilterBuilder):
    pass

class AsyncEventFilterBuilder(BaseEventFilterBuilder):
    pass
array_to_tuple = apply_formatter_if(is_list_like, tuple)

class BaseArgumentFilter(ABC):
    _match_values: Tuple[Any, ...] = None
    _immutable = False

    def __init__(self, arg_type: TypeStr) -> None:
        self.arg_type = arg_type

class DataArgumentFilter(BaseArgumentFilter):
    pass

class TopicArgumentFilter(BaseArgumentFilter):

    def __init__(self, arg_type: TypeStr, abi_codec: ABICodec) -> None:
        super().__init__(arg_type)
        self.abi_codec = abi_codec

class EventLogErrorFlags(Enum):
    Discard = 'discard'
    Ignore = 'ignore'
    Strict = 'strict'
    Warn = 'warn'
