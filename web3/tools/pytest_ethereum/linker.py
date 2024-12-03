import logging
from typing import Any, Callable, Dict
from eth_typing import ContractName
from eth_utils import to_checksum_address, to_hex
from eth_utils.toolz import assoc_in, curry, pipe
from ethpm import Package
from ethpm.uri import create_latest_block_uri
from web3.tools.pytest_ethereum._utils import create_deployment_data, get_deployment_address, insert_deployment
from web3.tools.pytest_ethereum.exceptions import LinkerError
logger = logging.getLogger('pytest_ethereum.linker')

def deploy(contract_name: str, *args: Any, transaction: Dict[str, Any]=None) -> Callable[..., Package]:
    """
    Return a newly created package and contract address.
    Will deploy the given contract_name, if data exists in package. If
    a deployment is found on the current w3 instance, it will return that deployment
    rather than creating a new instance.
    """
    def deployer(package: Package) -> Package:
        deployments = package.deployments
        if contract_name not in package.contract_types:
            raise DeployerError(contract_name, "Contract not found in package")
        
        w3 = package.w3
        if contains_matching_uri(deployments, w3):
            return package
        
        contract_factory = package.get_contract_factory(contract_name)
        try:
            deploy_transaction = contract_factory.constructor(*args).buildTransaction(transaction or {})
            tx_hash = w3.eth.send_transaction(deploy_transaction)
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            address = tx_receipt["contractAddress"]
        except Exception as e:
            raise DeployerError(contract_name, str(e))
        
        deployment_data = create_deployment_data(contract_name, address, tx_receipt)
        latest_block_uri = create_latest_block_uri(w3)
        manifest = insert_deployment(package, contract_name, deployment_data, latest_block_uri)
        return Package(manifest, w3)
    
    return deployer

@curry
def link(contract: ContractName, linked_type: str, package: Package) -> Package:
    """
    Return a new package, created with a new manifest after applying the linked type
    reference to the contract factory.
    """
    deployment_address = get_deployment_address(linked_type, package)
    unlinked_factory = package.get_contract_factory(contract)
    
    if not unlinked_factory.needs_bytecode_linking:
        raise LinkerError(contract, linked_type, "Contract does not require linking")
    
    linked_factory = unlinked_factory.link_bytecode({linked_type: deployment_address})
    
    # Update the contract factory in the package
    updated_manifest = assoc_in(
        package.manifest,
        ['contract_types', contract, 'deployment_bytecode', 'bytecode'],
        linked_factory.bytecode
    )
    
    return Package(updated_manifest, package.w3)

@curry
def run_python(callback_fn: Callable[..., None], package: Package) -> Package:
    """
    Return the unmodified package, after performing any user-defined
    callback function on the contracts in the package.
    """
    try:
        callback_fn(package)
    except Exception as e:
        logger.error(f"Error in callback function: {str(e)}")
    return package
