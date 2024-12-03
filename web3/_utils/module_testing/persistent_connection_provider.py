import asyncio
import pytest
from typing import TYPE_CHECKING, Any, Dict, Tuple, cast
from eth_utils import is_hexstr
from hexbytes import HexBytes
from web3.datastructures import AttributeDict
from web3.middleware import async_geth_poa_middleware
from web3.types import FormattedEthSubscriptionResponse
if TYPE_CHECKING:
    from web3.main import _PersistentConnectionWeb3

class PersistentConnectionProviderTest:
    async def test_persistent_connection(self, w3: "_PersistentConnectionWeb3") -> None:
        # Test that the connection is established
        assert w3.provider._ws is not None
        
        # Test basic RPC call
        block = await w3.eth.get_block('latest')
        assert isinstance(block, AttributeDict)
        assert 'number' in block
        
        # Test subscription
        async def callback(event: FormattedEthSubscriptionResponse) -> None:
            assert isinstance(event, AttributeDict)
            assert 'blockNumber' in event
        
        async with w3.eth.subscribe('newHeads', callback) as subscription:
            await asyncio.sleep(5)  # Wait for a few blocks
        
        # Test that the connection is still alive after subscription
        assert w3.provider._ws is not None
        
        # Test connection recovery
        await w3.provider.disconnect()
        assert w3.provider._ws is None
        
        # Wait for automatic reconnection
        await asyncio.sleep(2)
        assert w3.provider._ws is not None
        
        # Test that RPC calls still work after reconnection
        block = await w3.eth.get_block('latest')
        assert isinstance(block, AttributeDict)
        assert 'number' in block

    @pytest.mark.asyncio
    async def test_persistent_connection_context_manager(self, w3: "_PersistentConnectionWeb3") -> None:
        async with w3 as connected_w3:
            assert connected_w3.provider._ws is not None
            
            # Test basic RPC call within context
            block = await connected_w3.eth.get_block('latest')
            assert isinstance(block, AttributeDict)
            assert 'number' in block
        
        # Test that connection is closed after exiting context
        assert w3.provider._ws is None

    @pytest.mark.asyncio
    async def test_persistent_connection_iteration(self, w3: "_PersistentConnectionWeb3") -> None:
        iteration_count = 0
        async for connected_w3 in w3:
            assert connected_w3.provider._ws is not None
            
            # Test basic RPC call during iteration
            block = await connected_w3.eth.get_block('latest')
            assert isinstance(block, AttributeDict)
            assert 'number' in block
            
            iteration_count += 1
            if iteration_count >= 3:
                break
        
        assert iteration_count == 3
