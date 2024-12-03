import pytest
from typing import TYPE_CHECKING, List
from web3.datastructures import AttributeDict
from web3.types import EnodeURI
if TYPE_CHECKING:
    from web3 import AsyncWeb3, Web3

class GoEthereumAdminModuleTest:
    def test_admin_add_peer(self, web3: "Web3") -> None:
        enode = "enode://f1a6b0bdbf014355587c3018454d070ac57801f05d3b39fe85da574f002a32e929f683d72aa5a8318382e4d3c7a05c9b91687b0d997a39619fb8a6e7ad88e512@1.1.1.1:30303"
        result = web3.geth.admin.add_peer(enode)
        assert isinstance(result, bool)

    def test_admin_datadir(self, web3: "Web3") -> None:
        datadir = web3.geth.admin.datadir()
        assert isinstance(datadir, str)

    def test_admin_node_info(self, web3: "Web3") -> None:
        node_info = web3.geth.admin.node_info()
        assert isinstance(node_info, AttributeDict)
        assert 'enode' in node_info
        assert 'id' in node_info

    def test_admin_peers(self, web3: "Web3") -> None:
        peers = web3.geth.admin.peers()
        assert isinstance(peers, list)
        for peer in peers:
            assert isinstance(peer, AttributeDict)

    def test_admin_start_rpc(self, web3: "Web3") -> None:
        result = web3.geth.admin.start_rpc()
        assert isinstance(result, bool)

    def test_admin_start_ws(self, web3: "Web3") -> None:
        result = web3.geth.admin.start_ws()
        assert isinstance(result, bool)

    def test_admin_stop_rpc(self, web3: "Web3") -> None:
        result = web3.geth.admin.stop_rpc()
        assert isinstance(result, bool)

    def test_admin_stop_ws(self, web3: "Web3") -> None:
        result = web3.geth.admin.stop_ws()
        assert isinstance(result, bool)

class GoEthereumAsyncAdminModuleTest:
    @pytest.mark.asyncio
    async def test_admin_add_peer(self, async_w3: "AsyncWeb3") -> None:
        enode = "enode://f1a6b0bdbf014355587c3018454d070ac57801f05d3b39fe85da574f002a32e929f683d72aa5a8318382e4d3c7a05c9b91687b0d997a39619fb8a6e7ad88e512@1.1.1.1:30303"
        result = await async_w3.geth.admin.add_peer(enode)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_admin_datadir(self, async_w3: "AsyncWeb3") -> None:
        datadir = await async_w3.geth.admin.datadir()
        assert isinstance(datadir, str)

    @pytest.mark.asyncio
    async def test_admin_node_info(self, async_w3: "AsyncWeb3") -> None:
        node_info = await async_w3.geth.admin.node_info()
        assert isinstance(node_info, AttributeDict)
        assert 'enode' in node_info
        assert 'id' in node_info

    @pytest.mark.asyncio
    async def test_admin_peers(self, async_w3: "AsyncWeb3") -> None:
        peers = await async_w3.geth.admin.peers()
        assert isinstance(peers, list)
        for peer in peers:
            assert isinstance(peer, AttributeDict)

    @pytest.mark.asyncio
    async def test_admin_start_rpc(self, async_w3: "AsyncWeb3") -> None:
        result = await async_w3.geth.admin.start_rpc()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_admin_start_ws(self, async_w3: "AsyncWeb3") -> None:
        result = await async_w3.geth.admin.start_ws()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_admin_stop_rpc(self, async_w3: "AsyncWeb3") -> None:
        result = await async_w3.geth.admin.stop_rpc()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_admin_stop_ws(self, async_w3: "AsyncWeb3") -> None:
        result = await async_w3.geth.admin.stop_ws()
        assert isinstance(result, bool)
