import functools
import threading
from typing import Any, Callable, TypeVar, cast
import warnings
TFunc = TypeVar('TFunc', bound=Callable[..., Any])

def reject_recursive_repeats(to_wrap: Callable[..., Any]) -> Callable[..., Any]:
    """
    Prevent simple cycles by returning None when called recursively with same instance
    """
    @functools.wraps(to_wrap)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = args[0] if args else None
        thread_id = threading.get_ident()
        thread_local = threading.local()
        
        if not hasattr(thread_local, 'reject_recursive_repeats_track'):
            thread_local.reject_recursive_repeats_track = {}
        
        track = thread_local.reject_recursive_repeats_track
        
        if thread_id not in track:
            track[thread_id] = set()
        
        if instance in track[thread_id]:
            return None
        
        track[thread_id].add(instance)
        try:
            result = to_wrap(*args, **kwargs)
        finally:
            track[thread_id].remove(instance)
        
        return result
    
    return wrapper

def deprecate_method(replacement_method: str=None, deprecation_msg: str=None) -> Callable[..., Any]:
    """
    Decorate a deprecated function with info on its replacement method OR a clarifying
    reason for the deprecation.

    @deprecate_method("to_bytes()")
    def to_ascii(arg):
        ...

    @deprecate_method(deprecation_msg=(
        "This method is no longer supported and will be removed in the next release."
    ))
    def some_method(arg):
        ...
    """
    def decorator(func: TFunc) -> TFunc:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if replacement_method:
                warnings.warn(
                    f"{func.__name__} is deprecated. Use {replacement_method} instead.",
                    DeprecationWarning,
                    stacklevel=2
                )
            elif deprecation_msg:
                warnings.warn(
                    f"{func.__name__} is deprecated. {deprecation_msg}",
                    DeprecationWarning,
                    stacklevel=2
                )
            else:
                warnings.warn(
                    f"{func.__name__} is deprecated.",
                    DeprecationWarning,
                    stacklevel=2
                )
            return func(*args, **kwargs)
        return cast(TFunc, wrapper)
    return decorator
