class FallbackFn:
    """
    Identifier for the fallback function in Ethereum smart contracts.
    """
    selector = b''  # Fallback function has no selector

    @staticmethod
    def abi_signature():
        return 'fallback()'

class ReceiveFn:
    """
    Identifier for the receive function in Ethereum smart contracts.
    """
    selector = b''  # Receive function has no selector

    @staticmethod
    def abi_signature():
        return 'receive()'
