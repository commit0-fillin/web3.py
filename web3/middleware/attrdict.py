from typing import TYPE_CHECKING, Any, Callable, Optional, cast
from eth_utils.toolz import assoc
from web3.datastructures import AttributeDict
from web3.types import AsyncMiddlewareCoroutine, RPCEndpoint, RPCResponse
if TYPE_CHECKING:
    from web3 import AsyncWeb3, Web3
    from web3.providers import PersistentConnectionProvider

def attrdict_middleware(make_request: Callable[[RPCEndpoint, Any], Any], _w3: 'Web3') -> Callable[[RPCEndpoint, Any], RPCResponse]:
    """
    Converts any result which is a dictionary into an `AttributeDict`.

    Note: Accessing `AttributeDict` properties via attribute
        (e.g. my_attribute_dict.property1) will not preserve typing.
    """
    def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        response = make_request(method, params)

        if 'result' in response:
            result = response['result']
            if isinstance(result, dict):
                return assoc(response, 'result', AttributeDict(result))
            elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
                return assoc(response, 'result', [AttributeDict(item) for item in result])

        return response

    return middleware

async def async_attrdict_middleware(make_request: Callable[[RPCEndpoint, Any], Any], async_w3: 'AsyncWeb3') -> AsyncMiddlewareCoroutine:
    """
    Converts any result which is a dictionary into an `AttributeDict`.

    Note: Accessing `AttributeDict` properties via attribute
        (e.g. my_attribute_dict.property1) will not preserve typing.
    """
    async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        response = await make_request(method, params)

        if 'result' in response:
            result = response['result']
            if isinstance(result, dict):
                return assoc(response, 'result', AttributeDict(result))
            elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
                return assoc(response, 'result', [AttributeDict(item) for item in result])

        return response

    return middleware
