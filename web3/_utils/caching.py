import collections
import hashlib
from typing import TYPE_CHECKING, Any, Callable, List, Tuple
from eth_utils import is_boolean, is_bytes, is_dict, is_list_like, is_null, is_number, is_text, to_bytes
if TYPE_CHECKING:
    from web3.types import RPCEndpoint

def generate_cache_key(value: Any) -> str:
    """
    Generates a cache key for the *args and **kwargs
    """
    if is_null(value):
        return "null"
    elif is_boolean(value):
        return str(value).lower()
    elif is_number(value):
        return str(value)
    elif is_text(value):
        return hashlib.md5(value.encode('utf-8')).hexdigest()
    elif is_bytes(value):
        return hashlib.md5(value).hexdigest()
    elif is_list_like(value):
        return hashlib.md5(b''.join(generate_cache_key(item).encode('utf-8') for item in value)).hexdigest()
    elif is_dict(value):
        return hashlib.md5(b''.join(
            generate_cache_key(key).encode('utf-8') + generate_cache_key(val).encode('utf-8')
            for key, val in sorted(value.items())
        )).hexdigest()
    else:
        return hashlib.md5(str(value).encode('utf-8')).hexdigest()

class RequestInformation:

    def __init__(self, method: 'RPCEndpoint', params: Any, response_formatters: Tuple[Callable[..., Any], ...], subscription_id: str=None):
        self.method = method
        self.params = params
        self.response_formatters = response_formatters
        self.subscription_id = subscription_id
        self.middleware_response_processors: List[Callable[..., Any]] = []
