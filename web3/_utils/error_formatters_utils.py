import warnings
from eth_abi import abi
from eth_utils import to_bytes
from web3.exceptions import ContractCustomError, ContractLogicError, ContractPanicError, OffchainLookup, TransactionIndexingInProgress
from web3.types import RPCResponse
SOLIDITY_ERROR_FUNC_SELECTOR = '0x08c379a0'
OFFCHAIN_LOOKUP_FUNC_SELECTOR = '0x556f1830'
OFFCHAIN_LOOKUP_FIELDS = {'sender': 'address', 'urls': 'string[]', 'callData': 'bytes', 'callbackFunction': 'bytes4', 'extraData': 'bytes'}
PANIC_ERROR_FUNC_SELECTOR = '0x4e487b71'
PANIC_ERROR_CODES = {'00': 'Panic error 0x00: Generic compiler inserted panics.', '01': 'Panic error 0x01: Assert evaluates to false.', '11': 'Panic error 0x11: Arithmetic operation results in underflow or overflow.', '12': 'Panic error 0x12: Division by zero.', '21': 'Panic error 0x21: Cannot convert value into an enum type.', '22': 'Panic error 0x12: Storage byte array is incorrectly encoded.', '31': "Panic error 0x31: Call to 'pop()' on an empty array.", '32': 'Panic error 0x32: Array index is out of bounds.', '41': 'Panic error 0x41: Allocation of too much memory or array too large.', '51': 'Panic error 0x51: Call to a zero-initialized variable of internal function type.'}
MISSING_DATA = 'no data'

def _parse_error_with_reverted_prefix(data: str) -> str:
    """
    Parse errors from the data string which begin with the "Reverted" prefix.
    "Reverted", function selector and offset are always the same for revert errors
    """
    if data.startswith('Reverted '):
        # Remove "Reverted " prefix (9 characters)
        data = data[9:]
    
    # Function selector (4 bytes) and offset (32 bytes) are always the same
    # So we can skip the first 36 bytes (72 characters in hex)
    data = data[72:]
    
    # The next 32 bytes (64 characters) represent the string length
    str_length = int(data[:64], 16)
    
    # The remaining data is the actual error message
    error_message = to_bytes(hexstr=data[64:64 + str_length * 2]).decode('utf-8')
    
    return error_message

def _raise_contract_error(response_error_data: str) -> None:
    """
    Decode response error from data string and raise appropriate exception.

        "Reverted " (prefix may be present in `data`)
        Function selector for Error(string): 08c379a (4 bytes)
        Data offset: 32 (32 bytes)
        String length (32 bytes)
        Reason string (padded, use string length from above to get meaningful part)
    """
    if response_error_data.startswith(SOLIDITY_ERROR_FUNC_SELECTOR):
        # Remove function selector
        data = response_error_data[10:]
    elif response_error_data.startswith('Reverted '):
        data = response_error_data[9:]
    else:
        data = response_error_data

    # Parse the error message
    error_msg = _parse_error_with_reverted_prefix(data)

    if error_msg.startswith('execution reverted:'):
        error_msg = error_msg[20:].strip()

    raise ContractLogicError(error_msg, data)

def raise_contract_logic_error_on_revert(response: RPCResponse) -> RPCResponse:
    """
    Revert responses contain an error with the following optional attributes:
        `code` - in this context, used for an unknown edge case when code = '3'
        `message` - error message is passed to the raised exception
        `data` - response error details (str, dict, None)

    See also https://solidity.readthedocs.io/en/v0.6.3/control-structures.html#revert
    """
    if 'error' not in response:
        return response

    error = response['error']
    message = error.get('message', MISSING_DATA)
    data = error.get('data', MISSING_DATA)

    if error.get('code') == '3':
        raise ContractLogicError(message, data)

    if isinstance(data, str):
        if data.startswith(SOLIDITY_ERROR_FUNC_SELECTOR):
            _raise_contract_error(data)
        elif data.startswith(PANIC_ERROR_FUNC_SELECTOR):
            panic_code = data[10:12]
            panic_message = PANIC_ERROR_CODES.get(panic_code, f'Unknown panic code {panic_code}')
            raise ContractPanicError(panic_message, data)
        elif data.startswith(OFFCHAIN_LOOKUP_FUNC_SELECTOR):
            decoded_data = abi.decode(list(OFFCHAIN_LOOKUP_FIELDS.values()), to_bytes(hexstr=data[10:]))
            raise OffchainLookup(dict(zip(OFFCHAIN_LOOKUP_FIELDS.keys(), decoded_data)), data)

    if message.startswith('execution reverted:'):
        raise ContractLogicError(message[20:].strip(), data)
    elif message.startswith('revert'):
        raise ContractLogicError(message, data)
    elif data is MISSING_DATA:
        raise ContractLogicError(message, data)
    else:
        raise ContractLogicError(message, data)

    return response

def raise_transaction_indexing_error_if_indexing(response: RPCResponse) -> RPCResponse:
    """
    Raise an error if ``eth_getTransactionReceipt`` returns an error indicating that
    transactions are still being indexed.
    """
    if 'error' in response and response['error'].get('code') == -32001:
        raise TransactionIndexingInProgress(response['error'].get('message'))
    return response
