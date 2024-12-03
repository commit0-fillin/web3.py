from typing import Any, Dict, Iterable, List, Tuple
from eth_typing import URI, Address, ContractName, Manifest
from eth_utils import to_dict, to_hex, to_list
from eth_utils.toolz import assoc, assoc_in, dissoc
from ethpm import Package
from ethpm.uri import check_if_chain_matches_chain_uri
from web3 import Web3
from web3.tools.pytest_ethereum.exceptions import LinkerError
from web3.types import TxReceipt

def pluck_matching_uri(deployment_data: Dict[URI, Dict[str, str]], w3: Web3) -> URI:
    """
    Return any blockchain uri that matches w3-connected chain, if one
    is present in the deployment data keys.
    """
    for uri in deployment_data.keys():
        if check_if_chain_matches_chain_uri(w3, uri):
            return uri
    raise ValueError("No matching URI found for the connected chain")

def contains_matching_uri(deployment_data: Dict[str, Dict[str, str]], w3: Web3) -> bool:
    """
    Returns true if any blockchain uri in deployment data matches
    w3-connected chain.
    """
    return any(check_if_chain_matches_chain_uri(w3, uri) for uri in deployment_data.keys())

def insert_deployment(package: Package, deployment_name: str, deployment_data: Dict[str, str], latest_block_uri: URI) -> Manifest:
    """
    Returns a new manifest. If a matching chain uri is found
    in the old manifest, it will update the chain uri along
    with the new deployment data. If no match, it will simply add
    the new chain uri and deployment data.
    """
    old_deployments = package.manifest.get('deployments', {})
    
    if latest_block_uri in old_deployments:
        updated_deployments = assoc_in(
            old_deployments,
            [latest_block_uri, deployment_name],
            deployment_data
        )
    else:
        updated_deployments = assoc(
            old_deployments,
            latest_block_uri,
            {deployment_name: deployment_data}
        )
    
    return assoc(package.manifest, 'deployments', updated_deployments)

def get_deployment_address(linked_type: str, package: Package) -> Address:
    """
    Return the address of a linked_type found in a package's manifest deployments.
    """
    deployments = package.manifest.get('deployments', {})
    
    for deployment in deployments.values():
        if linked_type in deployment:
            return Address(deployment[linked_type]['address'])
    
    raise LinkerError(linked_type, "Package", f"Unable to find deployment of {linked_type}")
