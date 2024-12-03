from typing import TYPE_CHECKING, Optional, cast
from eth_typing import ChecksumAddress
from eth_utils.toolz import assoc, merge
from hexbytes import HexBytes
from web3._utils.transactions import prepare_replacement_transaction
from web3._utils.utility_methods import any_in_dict
from web3.constants import DYNAMIC_FEE_TXN_PARAMS
from web3.types import BlockIdentifier, TxData, TxParams, Wei, _Hash32
if TYPE_CHECKING:
    from web3.eth import AsyncEth
    from web3.main import AsyncWeb3
TRANSACTION_DEFAULTS = {'value': 0, 'data': b'', 'gas': _estimate_gas, 'gasPrice': lambda async_w3, tx: async_w3.eth.generate_gas_price(tx), 'maxFeePerGas': _max_fee_per_gas, 'maxPriorityFeePerGas': _max_priority_fee_gas, 'chainId': _chain_id}

async def async_fill_transaction_defaults(async_w3: 'AsyncWeb3', transaction: TxParams) -> TxParams:
    """
    if async_w3 is None, fill as much as possible while offline
    """
    filled_transaction = transaction.copy()

    if async_w3 is None:
        # Fill only static defaults when offline
        for key, default_value in TRANSACTION_DEFAULTS.items():
            if key not in filled_transaction and not callable(default_value):
                filled_transaction[key] = default_value
    else:
        # Fill all defaults when online
        for key, default_value in TRANSACTION_DEFAULTS.items():
            if key not in filled_transaction:
                if callable(default_value):
                    if key == 'gas':
                        filled_transaction[key] = await async_w3.eth.estimate_gas(filled_transaction)
                    elif key == 'gasPrice':
                        filled_transaction[key] = await async_w3.eth.generate_gas_price(filled_transaction)
                    elif key == 'maxFeePerGas':
                        max_priority_fee = await async_w3.eth.max_priority_fee
                        latest_block = await async_w3.eth.get_block('latest')
                        filled_transaction[key] = max_priority_fee + 2 * latest_block['baseFeePerGas']
                    elif key == 'maxPriorityFeePerGas':
                        filled_transaction[key] = await async_w3.eth.max_priority_fee
                    elif key == 'chainId':
                        filled_transaction[key] = await async_w3.eth.chain_id
                    else:
                        filled_transaction[key] = default_value(async_w3, filled_transaction)
                else:
                    filled_transaction[key] = default_value

    # Ensure all keys in the transaction are valid
    invalid_keys = set(filled_transaction.keys()) - set(VALID_TRANSACTION_PARAMS)
    if invalid_keys:
        raise ValueError(f"Invalid transaction parameters: {', '.join(invalid_keys)}")

    # Handle EIP-1559 transactions
    if 'gasPrice' in filled_transaction and any_in_dict(DYNAMIC_FEE_TXN_PARAMS, filled_transaction):
        raise ValueError("Transaction cannot contain both 'gasPrice' and ('maxFeePerGas' or 'maxPriorityFeePerGas')")

    if any_in_dict(DYNAMIC_FEE_TXN_PARAMS, filled_transaction) and 'type' not in filled_transaction:
        filled_transaction['type'] = '0x2'  # EIP-1559 transaction type

    return filled_transaction
