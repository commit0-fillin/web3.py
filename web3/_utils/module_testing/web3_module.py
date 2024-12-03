import pytest
from typing import Any, NoReturn, Sequence, Union
from eth_typing import ChecksumAddress, HexAddress, HexStr, TypeStr
from hexbytes import HexBytes
from web3 import AsyncWeb3, Web3
from web3._utils.ens import ens_addresses
from web3.exceptions import InvalidAddress

class Web3ModuleTest:
    def test_web3_clientVersion(self, web3: Union[Web3, AsyncWeb3]) -> None:
        client_version = web3.clientVersion
        assert isinstance(client_version, str)
        assert len(client_version) > 0

    def test_web3_api(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert isinstance(web3.api, str)
        assert web3.api.startswith("web3/")

    def test_web3_is_connected(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.isConnected()

    def test_web3_to_hex(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toHex(0) == '0x0'
        assert web3.toHex(1) == '0x1'
        assert web3.toHex(15) == '0xf'
        assert web3.toHex(16) == '0x10'
        assert web3.toHex(255) == '0xff'
        assert web3.toHex('0x0') == '0x0'
        assert web3.toHex('0x1') == '0x1'
        assert web3.toHex('0xf') == '0xf'
        assert web3.toHex('0x10') == '0x10'
        assert web3.toHex('0xff') == '0xff'
        assert web3.toHex('0x0123456789abcdef') == '0x0123456789abcdef'

    def test_web3_to_text(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toText(HexStr('0x68656c6c6f20776f726c64')) == 'hello world'
        assert web3.toText('0x68656c6c6f20776f726c64') == 'hello world'
        assert web3.toText(b'hello world') == 'hello world'

    def test_web3_to_bytes(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toBytes(0) == b'\x00'
        assert web3.toBytes(1) == b'\x01'
        assert web3.toBytes(15) == b'\x0f'
        assert web3.toBytes(16) == b'\x10'
        assert web3.toBytes(255) == b'\xff'
        assert web3.toBytes('0x0') == b'\x00'
        assert web3.toBytes('0x1') == b'\x01'
        assert web3.toBytes('0xf') == b'\x0f'
        assert web3.toBytes('0x10') == b'\x10'
        assert web3.toBytes('0xff') == b'\xff'
        assert web3.toBytes('0x0123456789abcdef') == b'\x01\x23\x45\x67\x89\xab\xcd\xef'

    def test_web3_to_int(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toInt(0) == 0
        assert web3.toInt(1) == 1
        assert web3.toInt('0x0') == 0
        assert web3.toInt('0x1') == 1
        assert web3.toInt('0x10') == 16
        assert web3.toInt('0xff') == 255
        assert web3.toInt('0x0123456789abcdef') == 81985529216486895

    def test_web3_to_json(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toJSON({'test': 'value'}) == '{"test": "value"}'
        assert web3.toJSON(['test', 'value']) == '["test", "value"]'
        assert web3.toJSON(1) == '1'
        assert web3.toJSON('test') == '"test"'

    def test_web3_from_wei(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.fromWei(1, 'wei') == 1
        assert web3.fromWei(1000000000000000000, 'ether') == 1
        assert web3.fromWei(1, 'ether') == 0.000000000000000001

    def test_web3_to_wei(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toWei(1, 'wei') == 1
        assert web3.toWei(1, 'ether') == 1000000000000000000
        assert web3.toWei(0.000000000000000001, 'ether') == 1

    def test_web3_keccak(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.keccak(text='test').hex() == '0x9c22ff5f21f0b81b113e63f7db6da94fedef11b2119b4088b89664fb9a3cb658'
        assert web3.keccak(hexstr='0x74657374').hex() == '0x9c22ff5f21f0b81b113e63f7db6da94fedef11b2119b4088b89664fb9a3cb658'
        assert web3.keccak(b'test').hex() == '0x9c22ff5f21f0b81b113e63f7db6da94fedef11b2119b4088b89664fb9a3cb658'

    def test_web3_solidity_keccak(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.solidityKeccak(['bool'], [True]).hex() == '0x5fe7f977e71dba2ea1a68e21057beebb9be2ac30c6410aa38d4f3fbe41dcffd2'
        assert web3.solidityKeccak(['uint8', 'uint8', 'uint8'], [97, 98, 99]).hex() == '0x4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45'
        assert web3.solidityKeccak(['address'], ['0x49EdDD3769c0712032808D86597B84ac5c2F5614']).hex() == '0x2ff37b5607484cd4eecf6d13292e22bd6e5401eaffcc07e279583bc742c68882'

    def test_is_address(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.isAddress('0x49EdDD3769c0712032808D86597B84ac5c2F5614') is True
        assert web3.isAddress('0x49eddd3769c0712032808d86597b84ac5c2f5614') is True
        assert web3.isAddress('0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B') is True
        assert web3.isAddress('not_a_valid_address') is False
        assert web3.isAddress('0xinvalidaddress') is False

    def test_is_checksum_address(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.isChecksumAddress('0x49EdDD3769c0712032808D86597B84ac5c2F5614') is True
        assert web3.isChecksumAddress('0x49eddd3769c0712032808d86597b84ac5c2f5614') is False
        assert web3.isChecksumAddress('0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B') is True
        assert web3.isChecksumAddress('not_a_valid_address') is False

    def test_to_checksum_address(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.toChecksumAddress('0x49eddd3769c0712032808d86597b84ac5c2f5614') == '0x49EdDD3769c0712032808D86597B84ac5c2F5614'
        assert web3.toChecksumAddress('0xab5801a7d398351b8be11c439e05c5b3259aec9b') == '0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B'

        with pytest.raises(InvalidAddress):
            web3.toChecksumAddress('not_a_valid_address')

    def test_is_connected(self, web3: Union[Web3, AsyncWeb3]) -> None:
        assert web3.isConnected() is True
