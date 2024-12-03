class PytestEthereumError(Exception):
    """
    Base class for all Pytest-Ethereum errors.
    """
    def __init__(self, message="An error occurred in Pytest-Ethereum"):
        self.message = message
        super().__init__(self.message)

class DeployerError(PytestEthereumError):
    """
    Raised when the Deployer is unable to deploy a contract type.
    """
    def __init__(self, contract_name, reason):
        self.contract_name = contract_name
        self.reason = reason
        message = f"Failed to deploy contract '{contract_name}': {reason}"
        super().__init__(message)

class LinkerError(PytestEthereumError):
    """
    Raised when the Linker is unable to link two contract types.
    """
    def __init__(self, contract1, contract2, reason):
        self.contract1 = contract1
        self.contract2 = contract2
        self.reason = reason
        message = f"Failed to link contracts '{contract1}' and '{contract2}': {reason}"
        super().__init__(message)
