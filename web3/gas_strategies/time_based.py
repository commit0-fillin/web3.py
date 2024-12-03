import collections
import math
import operator
from typing import Iterable, Sequence, Tuple
from eth_typing import ChecksumAddress
from eth_utils import to_tuple
from eth_utils.toolz import curry, groupby, sliding_window
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.math import percentile
from web3.exceptions import InsufficientData, Web3ValidationError
from web3.types import BlockNumber, GasPriceStrategy, TxParams, Wei
MinerData = collections.namedtuple('MinerData', ['miner', 'num_blocks', 'min_gas_price', 'low_percentile_gas_price'])
Probability = collections.namedtuple('Probability', ['gas_price', 'prob'])

@to_tuple
def _compute_probabilities(miner_data: Iterable[MinerData], wait_blocks: int, sample_size: int) -> Iterable[Probability]:
    """
    Computes the probabilities that a txn will be accepted at each of the gas
    prices accepted by the miners.
    """
    miner_data_list = list(miner_data)
    total_blocks = sum(miner.num_blocks for miner in miner_data_list)

    for miner in miner_data_list:
        num_blocks_to_wait = wait_blocks
        for _, sliding_window in groupby(sliding_window(sample_size, miner_data_list), key=operator.itemgetter(0)):
            sliding_window = list(sliding_window)
            if miner == sliding_window[0][0]:
                num_blocks_to_wait -= sum(window.num_blocks for window in sliding_window)
                if num_blocks_to_wait <= 0:
                    break

        probability = float(max(0, min(1, miner.num_blocks / total_blocks * sample_size / wait_blocks)))
        yield Probability(miner.low_percentile_gas_price, probability)

def _compute_gas_price(probabilities: Sequence[Probability], desired_probability: float) -> Wei:
    """
    Given a sorted range of ``Probability`` named-tuples returns a gas price
    computed based on where the ``desired_probability`` would fall within the
    range.

    :param probabilities: An iterable of `Probability` named-tuples
        sorted in reverse order.
    :param desired_probability: An floating point representation of the desired
        probability. (e.g. ``85% -> 0.85``)
    """
    if not probabilities:
        raise InsufficientData("No probabilities provided")

    if desired_probability < 0 or desired_probability > 1:
        raise ValueError("Desired probability must be between 0 and 1")

    for idx, probability in enumerate(probabilities[:-1]):
        next_probability = probabilities[idx + 1]
        if probability.prob >= desired_probability > next_probability.prob:
            range_size = probability.prob - next_probability.prob
            if range_size > 0:
                position = (desired_probability - next_probability.prob) / range_size
                gas_price_range = probability.gas_price - next_probability.gas_price
                estimated_gas_price = int(next_probability.gas_price + position * gas_price_range)
                return Wei(estimated_gas_price)

    return Wei(probabilities[-1].gas_price)

@curry
def construct_time_based_gas_price_strategy(max_wait_seconds: int, sample_size: int=120, probability: int=98, weighted: bool=False) -> GasPriceStrategy:
    """
    A gas pricing strategy that uses recently mined block data to derive a gas
    price for which a transaction is likely to be mined within X seconds with
    probability P. If the weighted kwarg is True, more recent block
    times will be more heavily weighted.

    :param max_wait_seconds: The desired maximum number of seconds the
        transaction should take to mine.
    :param sample_size: The number of recent blocks to sample
    :param probability: An integer representation of the desired probability
        that the transaction will be mined within ``max_wait_seconds``.  0 means 0%
        and 100 means 100%.
    """
    def time_based_gas_price_strategy(web3: Web3, transaction_params: TxParams) -> Wei:
        if probability < 0 or probability > 100:
            raise ValueError("Probability must be between 0 and 100")

        if sample_size < 1:
            raise ValueError("Sample size must be at least 1")

        latest_block = web3.eth.get_block('latest')
        latest_block_number = latest_block['number']

        # Collect block data
        blocks = [web3.eth.get_block(latest_block_number - i) for i in range(sample_size)]

        # Calculate average block time
        block_time = sum(b1['timestamp'] - b2['timestamp'] for b1, b2 in zip(blocks[:-1], blocks[1:])) / (sample_size - 1)

        wait_blocks = int(max_wait_seconds / block_time)

        # Group blocks by miner
        miner_groups = groupby(blocks, key=lambda b: b['miner'])
        miner_data = [
            MinerData(
                miner=miner,
                num_blocks=len(list(blocks)),
                min_gas_price=min(int(b['baseFeePerGas']) for b in blocks),
                low_percentile_gas_price=percentile([int(b['baseFeePerGas']) for b in blocks], 20)
            )
            for miner, blocks in miner_groups
        ]

        probabilities = _compute_probabilities(miner_data, wait_blocks, sample_size)
        desired_probability = probability / 100.0

        gas_price = _compute_gas_price(probabilities, desired_probability)

        return gas_price

    return time_based_gas_price_strategy
fast_gas_price_strategy = construct_time_based_gas_price_strategy(max_wait_seconds=60, sample_size=120)
medium_gas_price_strategy = construct_time_based_gas_price_strategy(max_wait_seconds=600, sample_size=120)
slow_gas_price_strategy = construct_time_based_gas_price_strategy(max_wait_seconds=60 * 60, sample_size=120)
glacial_gas_price_strategy = construct_time_based_gas_price_strategy(max_wait_seconds=24 * 60 * 60, sample_size=720)
