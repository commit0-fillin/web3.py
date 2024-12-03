from typing import Optional, Any
from web3._utils.rpc_abi import RPC
from web3.module import Module

class Testing(Module):
    def timeTravel(self, timestamp: int) -> bool:
        """
        Fast forward the time of the blockchain to a future timestamp.
        
        :param timestamp: The timestamp to fast forward to.
        :return: True if successful, False otherwise.
        """
        return self.web3.manager.request_blocking(RPC.testing_timeTravel, [timestamp])

    def mine(self, num_blocks: int = 1) -> bool:
        """
        Mine a specified number of blocks.
        
        :param num_blocks: The number of blocks to mine. Defaults to 1.
        :return: True if successful, False otherwise.
        """
        return self.web3.manager.request_blocking(RPC.evm_mine, [num_blocks])

    def snapshot(self) -> Any:
        """
        Create a snapshot of the current blockchain state.
        
        :return: The snapshot id.
        """
        return self.web3.manager.request_blocking(RPC.evm_snapshot, [])

    def revert(self, snapshot_id: Any) -> bool:
        """
        Revert the blockchain to a previous snapshot.
        
        :param snapshot_id: The id of the snapshot to revert to.
        :return: True if successful, False otherwise.
        """
        return self.web3.manager.request_blocking(RPC.evm_revert, [snapshot_id])

    def reset_to_genesis(self) -> bool:
        """
        Reset the blockchain to its genesis state.
        
        :return: True if successful, False otherwise.
        """
        return self.web3.manager.request_blocking(RPC.evm_reset, [])

    def set_account_balance(self, address: str, balance: int) -> bool:
        """
        Set the balance of an account to a specific value.
        
        :param address: The address of the account.
        :param balance: The new balance in wei.
        :return: True if successful, False otherwise.
        """
        return self.web3.manager.request_blocking(RPC.testing_setAccountBalance, [address, balance])
