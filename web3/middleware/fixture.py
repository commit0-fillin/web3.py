from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, cast
from web3.types import AsyncMiddleware, AsyncMiddlewareCoroutine, Middleware, RPCEndpoint, RPCResponse
if TYPE_CHECKING:
    from web3.main import AsyncWeb3, Web3
    from web3.providers import PersistentConnectionProvider

def construct_fixture_middleware(fixtures: Dict[RPCEndpoint, Any]) -> Middleware:
    """
    Constructs a middleware which returns a static response for any method
    which is found in the provided fixtures.
    """
    def fixture_middleware(make_request: Callable[[RPCEndpoint, Any], Any], web3: "Web3") -> Callable[[RPCEndpoint, Any], RPCResponse]:
        def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method in fixtures:
                return {"result": fixtures[method]}
            return make_request(method, params)
        return middleware
    return fixture_middleware

def construct_result_generator_middleware(result_generators: Dict[RPCEndpoint, Any]) -> Middleware:
    """
    Constructs a middleware which intercepts requests for any method found in
    the provided mapping of endpoints to generator functions, returning
    whatever response the generator function returns.  Callbacks must be
    functions with the signature `fn(method, params)`.
    """
    def result_generator_middleware(make_request: Callable[[RPCEndpoint, Any], Any], web3: "Web3") -> Callable[[RPCEndpoint, Any], RPCResponse]:
        def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method in result_generators:
                result = result_generators[method](method, params)
                return {"result": result}
            return make_request(method, params)
        return middleware
    return result_generator_middleware

def construct_error_generator_middleware(error_generators: Dict[RPCEndpoint, Any]) -> Middleware:
    """
    Constructs a middleware which intercepts requests for any method found in
    the provided mapping of endpoints to generator functions, returning
    whatever error message the generator function returns.  Callbacks must be
    functions with the signature `fn(method, params)`.
    """
    def error_generator_middleware(make_request: Callable[[RPCEndpoint, Any], Any], web3: "Web3") -> Callable[[RPCEndpoint, Any], RPCResponse]:
        def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method in error_generators:
                error = error_generators[method](method, params)
                return {"error": error}
            return make_request(method, params)
        return middleware
    return error_generator_middleware

async def async_construct_result_generator_middleware(result_generators: Dict[RPCEndpoint, Any]) -> AsyncMiddleware:
    """
    Constructs a middleware which returns a static response for any method
    which is found in the provided fixtures.
    """
    async def async_result_generator_middleware(make_request: Callable[[RPCEndpoint, Any], Any], web3: "AsyncWeb3") -> AsyncMiddlewareCoroutine:
        async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method in result_generators:
                result = await result_generators[method](method, params)
                return {"result": result}
            return await make_request(method, params)
        return middleware
    return async_result_generator_middleware

async def async_construct_error_generator_middleware(error_generators: Dict[RPCEndpoint, Any]) -> AsyncMiddleware:
    """
    Constructs a middleware which intercepts requests for any method found in
    the provided mapping of endpoints to generator functions, returning
    whatever error message the generator function returns.  Callbacks must be
    functions with the signature `fn(method, params)`.
    """
    async def async_error_generator_middleware(make_request: Callable[[RPCEndpoint, Any], Any], web3: "AsyncWeb3") -> AsyncMiddlewareCoroutine:
        async def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
            if method in error_generators:
                error = await error_generators[method](method, params)
                return {"error": error}
            return await make_request(method, params)
        return middleware
    return async_error_generator_middleware
