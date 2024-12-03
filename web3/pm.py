from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Any, Dict, Iterable, NamedTuple, Tuple, Type, TypeVar, Union, cast
from eth_typing import URI, Address, ChecksumAddress, ContractName, Manifest
from eth_utils import is_canonical_address, is_checksum_address, to_checksum_address, to_text, to_tuple
from ens import ENS
from ethpm import ASSETS_DIR, Package
from ethpm.exceptions import EthPMException, ManifestValidationError
from ethpm.uri import is_supported_content_addressed_uri, resolve_uri_contents
from ethpm.validation.manifest import validate_manifest_against_schema, validate_raw_manifest_format
from ethpm.validation.package import validate_package_name, validate_package_version
from web3 import Web3
from web3._utils.ens import is_ens_name
from web3.exceptions import InvalidAddress, NameNotFound
from web3.module import Module
T = TypeVar('T')

class ReleaseData(NamedTuple):
    package_name: str
    version: str
    manifest_uri: URI

class ERC1319Registry(ABC):
    """
    The ERC1319Registry class is a base class for all registry implementations
    to inherit from. It defines the methods specified in
    `ERC 1319 <https://github.com/ethereum/EIPs/issues/1319>`__.  All of these
    methods are prefixed with an underscore, since they are not intended to be
    accessed directly, but rather through the methods on ``web3.pm``.
    They are unlikely to change, but must be implemented in a `ERC1319Registry`
    subclass in order to be compatible with the `PM` module. Any custom
    methods (eg. not defined in ERC1319) in a subclass should *not* be
    prefixed with an underscore.

    All of these methods must be implemented in any subclass in order to work
    with `web3.pm.PM`. Any implementation specific logic should be
    handled in a subclass.
    """

    @abstractmethod
    def __init__(self, address: Address, w3: Web3) -> None:
        """
        Initializes the class with the on-chain address of the registry, and a web3
        instance connected to the chain where the registry can be found.

        Must set the following properties...

        * ``self.registry``: A `web3.contract` instance of the target registry.
        * ``self.address``: The address of the target registry.
        * ``self.w3``: The *web3* instance connected to the chain where the
                       registry can be found.
        """
        pass

    @abstractmethod
    def _release(self, package_name: str, version: str, manifest_uri: str) -> bytes:
        """
        Returns the releaseId created by successfully adding a release to the registry.

        * Parameters:
            * ``package_name``: Valid package name according the spec.
            * ``version``: Version identifier string, can conform to
                           any versioning scheme.
            * ``manifest_uri``: URI location of a manifest which details the
                                release contents
        """
        pass

    @abstractmethod
    def _get_package_name(self, package_id: bytes) -> str:
        """
        Returns the package name associated with the given package id, if the
        package id exists on the connected registry.

        * Parameters:
            * ``package_id``: 32 byte package identifier.
        """
        pass

    @abstractmethod
    def _get_all_package_ids(self) -> Iterable[bytes]:
        """
        Returns a tuple containing all of the package ids found on the
        connected registry.
        """
        pass

    @abstractmethod
    def _get_release_id(self, package_name: str, version: str) -> bytes:
        """
        Returns the 32 bytes release id associated with the given
        package name and version, if the release exists on the connected registry.

        * Parameters:
            * ``package_name``: Valid package name according the spec.
            * ``version``: Version identifier string, can conform to
                           any versioning scheme.
        """
        pass

    @abstractmethod
    def _get_all_release_ids(self, package_name: str) -> Iterable[bytes]:
        """
        Returns a tuple containing all of the release ids belonging to the
        given package name, if the package has releases on the connected registry.

        * Parameters:
            * ``package_name``: Valid package name according the spec.
        """
        pass

    @abstractmethod
    def _get_release_data(self, release_id: bytes) -> ReleaseData:
        """
        Returns a tuple containing (package_name, version, manifest_uri) for the
        given release id, if the release exists on the connected registry.

        * Parameters:
            * ``release_id``: 32 byte release identifier.
        """
        pass

    @abstractmethod
    def _generate_release_id(self, package_name: str, version: str) -> bytes:
        """
        Returns the 32 byte release identifier that *would* be associated with the given
        package name and version according to the registry's hashing mechanism.
        The release *does not* have to exist on the connected registry.

        * Parameters:
            * ``package_name``: Valid package name according the spec.
            * ``version``: Version identifier string, can conform to
                           any versioning scheme.
        """
        pass

    @abstractmethod
    def _num_package_ids(self) -> int:
        """
        Returns the number of packages that exist on the connected registry.
        """
        pass

    @abstractmethod
    def _num_release_ids(self, package_name: str) -> int:
        """
        Returns the number of releases found on the connected registry,
        that belong to the given package name.

        * Parameters:
            * ``package_name``: Valid package name according the spec.
        """
        pass

    @classmethod
    @abstractmethod
    def deploy_new_instance(cls: Type[T], w3: Web3) -> T:
        """
        Class method that returns a newly deployed instance of ERC1319Registry.

        * Parameters:
            * ``w3``: Web3 instance on which to deploy the new registry.
        """
        pass
BATCH_SIZE = 100

class SimpleRegistry(ERC1319Registry):
    """
    This class represents an instance of the `Solidity Reference Registry implementation
    <https://github.com/ethpm/solidity-registry>`__.
    """

    def __init__(self, address: ChecksumAddress, w3: Web3) -> None:
        abi = get_simple_registry_manifest()['contractTypes']['PackageRegistry']['abi']
        self.registry = w3.eth.contract(address=address, abi=abi)
        self.address = address
        self.w3 = w3

    def _release(self, package_name: str, version: str, manifest_uri: str) -> bytes:
        tx_hash = self.registry.functions.release(package_name, version, manifest_uri).transact()
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.registry.events.VersionRelease().process_receipt(tx_receipt)[0]['args']['releaseId']

    def _get_package_name(self, package_id: bytes) -> str:
        return self.registry.functions.getPackageName(package_id).call()

    def _get_all_package_ids(self) -> Iterable[bytes]:
        package_count = self._num_package_ids()
        return [self.registry.functions.getPackageNameHash(i).call() for i in range(package_count)]

    def _get_release_id(self, package_name: str, version: str) -> bytes:
        return self.registry.functions.getReleaseId(package_name, version).call()

    def _get_all_release_ids(self, package_name: str) -> Iterable[bytes]:
        release_count = self._num_release_ids(package_name)
        return [self.registry.functions.getReleaseId(package_name, i).call() for i in range(release_count)]

    def _get_release_data(self, release_id: bytes) -> ReleaseData:
        data = self.registry.functions.getReleaseData(release_id).call()
        return ReleaseData(package_name=data[0], version=data[1], manifest_uri=data[2])

    def _generate_release_id(self, package_name: str, version: str) -> bytes:
        return self.registry.functions.generateReleaseId(package_name, version).call()

    def _num_package_ids(self) -> int:
        return self.registry.functions.numPackageIds().call()

    def _num_release_ids(self, package_name: str) -> int:
        return self.registry.functions.numReleaseIds(package_name).call()

    @classmethod
    def deploy_new_instance(cls: Type[T], w3: Web3) -> T:
        manifest = get_simple_registry_manifest()
        contract_type = manifest['contractTypes']['PackageRegistry']
        deployment_bytecode = contract_type['deploymentBytecode']['bytecode']
        abi = contract_type['abi']

        contract = w3.eth.contract(abi=abi, bytecode=deployment_bytecode)
        tx_hash = contract.constructor().transact()
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return cls(tx_receipt.contractAddress, w3)

class PM(Module):
    """
    The PM module will work with any subclass of ``ERC1319Registry``,
    tailored to a particular implementation of
    `ERC1319  <https://github.com/ethereum/EIPs/issues/1319>`__, set as
    its ``registry`` attribute.
    """
    w3: 'Web3'

    def get_package_from_manifest(self, manifest: Manifest) -> Package:
        """
        Returns a `Package <https://github.com/ethpm/py-ethpm/blob/master/ethpm/package.py>`__  # noqa: E501
        instance built with the given manifest.

        * Parameters:
            * ``manifest``: A dict representing a valid manifest
        """
        return Package(manifest, self.w3)

    def get_package_from_uri(self, manifest_uri: URI) -> Package:
        """
        Returns a `Package <https://github.com/ethpm/py-ethpm/blob/master/ethpm/package.py>`__  # noqa: E501
        instance built with the Manifest stored at the URI.
        If you want to use a specific IPFS backend, set ``ETHPM_IPFS_BACKEND_CLASS``
        to your desired backend. Defaults to Infura IPFS backend.

        * Parameters:
            * ``uri``: Must be a valid content-addressed URI
        """
        manifest = resolve_uri_contents(manifest_uri)
        return self.get_package_from_manifest(manifest)

    def get_local_package(self, package_name: str, ethpm_dir: Path=None) -> Package:
        """
        Returns a `Package <https://github.com/ethpm/py-ethpm/blob/master/ethpm/package.py>`__  # noqa: E501
        instance built with the Manifest found at the package name in your local ethpm_dir.

        * Parameters:
            * ``package_name``: Must be the name of a package installed locally.
            * ``ethpm_dir``: Path pointing to the target ethpm directory (optional).
        """
        if ethpm_dir is None:
            ethpm_dir = Path.cwd() / 'ethpm_packages'
        manifest_path = ethpm_dir / package_name / 'manifest.json'
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at: {manifest_path}")
        with open(manifest_path) as f:
            manifest = json.load(f)
        return self.get_package_from_manifest(manifest)

    def set_registry(self, address: Union[Address, ChecksumAddress, ENS]) -> None:
        """
        Sets the current registry used in ``web3.pm`` functions that read/write
        to an on-chain registry. This method accepts checksummed/canonical
        addresses or ENS names. Addresses must point to an on-chain instance
        of an ERC1319 registry implementation.

        To use an ENS domain as the address, make sure a valid ENS instance
        set as ``web3.ens``.

        * Parameters:
            * ``address``: Address of on-chain Registry.
        """
        if isinstance(address, str) and is_ens_name(address):
            resolved_address = self.w3.ens.address(address)
            if resolved_address is None:
                raise NameNotFound(f"No address found for ENS name: {address}")
            address = resolved_address
        self.registry = SimpleRegistry(address, self.w3)

    def deploy_and_set_registry(self) -> ChecksumAddress:
        """
        Returns the address of a freshly deployed instance of `SimpleRegistry`
        and sets the newly deployed registry as the active registry on
        ``web3.pm.registry``.

        To tie your registry to an ENS name, use web3's ENS module, ie.

        .. code-block:: python

           w3.ens.setup_address(ens_name, w3.pm.registry.address)
        """
        self.registry = SimpleRegistry.deploy_new_instance(self.w3)
        return self.registry.address

    def release_package(self, package_name: str, version: str, manifest_uri: URI) -> bytes:
        """
        Returns the release id generated by releasing a package on the current registry.
        Requires ``web3.PM`` to have a registry set. Requires
        ``web3.eth.default_account`` to be the registry owner.

        * Parameters:
            * ``package_name``: Must be a valid package name, matching the
                                given manifest.
            * ``version``: Must be a valid package version, matching the given manifest.
            * ``manifest_uri``: Must be a valid content-addressed URI. Currently,
                                only IPFS and Github content-addressed URIs are
                                supported.

        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        return self.registry._release(package_name, version, manifest_uri)

    @to_tuple
    def get_all_package_names(self) -> Iterable[str]:
        """
        Returns a tuple containing all the package names
        available on the current registry.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        for package_id in self.registry._get_all_package_ids():
            yield self.registry._get_package_name(package_id)

    def get_package_count(self) -> int:
        """
        Returns the number of packages available on the current registry.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        return self.registry._num_package_ids()

    def get_release_count(self, package_name: str) -> int:
        """
        Returns the number of releases of the given package name
        available on the current registry.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        return self.registry._num_release_ids(package_name)

    def get_release_id(self, package_name: str, version: str) -> bytes:
        """
        Returns the 32 byte identifier of a release for the given package
        name and version, if they are available on the current registry.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        return self.registry._get_release_id(package_name, version)

    @to_tuple
    def get_all_package_releases(self, package_name: str) -> Iterable[Tuple[str, str]]:
        """
        Returns a tuple of release data (version, manifest_ur) for every release of the
        given package name available on the current registry.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        for release_id in self.registry._get_all_release_ids(package_name):
            release_data = self.registry._get_release_data(release_id)
            yield (release_data.version, release_data.manifest_uri)

    def get_release_id_data(self, release_id: bytes) -> ReleaseData:
        """
        Returns ``(package_name, version, manifest_uri)`` associated with the given
        release id, *if* it is available on the current registry.

        * Parameters:
            * ``release_id``: 32 byte release identifier
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        return self.registry._get_release_data(release_id)

    def get_release_data(self, package_name: str, version: str) -> ReleaseData:
        """
        Returns ``(package_name, version, manifest_uri)`` associated with the given
        package name and version, *if* they are published to the currently set registry.

        * Parameters:
            * ``name``: Must be a valid package name.
            * ``version``: Must be a valid package version.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        release_id = self.get_release_id(package_name, version)
        return self.get_release_id_data(release_id)

    def get_package(self, package_name: str, version: str) -> Package:
        """
        Returns a ``Package`` instance, generated by the ``manifest_uri``
        associated with the given package name and version, if they are
        published to the currently set registry.

        * Parameters:
            * ``name``: Must be a valid package name.
            * ``version``: Must be a valid package version.
        """
        if not self.registry:
            raise ValueError("Registry not set. Call set_registry() first.")
        release_data = self.get_release_data(package_name, version)
        manifest_uri = release_data.manifest_uri
        return self.get_package_from_uri(manifest_uri)
