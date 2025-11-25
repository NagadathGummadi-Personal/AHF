from typing import TypeVar, Union, Any, Callable, NoReturn, Generic
from abc import ABC, abstractmethod
from Helpers.ExceptionHelper import UnwrapError
from Helpers.constants import EXPORT_CONSTANTS, ERRORCONSTANTS

__all__ = [
    EXPORT_CONSTANTS.Result, EXPORT_CONSTANTS.ResultType
]

T = TypeVar('T')
E = TypeVar('E')
F = TypeVar('F')

class BaseResult(ABC, Generic[T]):
    def is_ok(self) -> bool: return False
    def is_err(self) -> bool: return False
    def is_feedback(self) -> bool: return False

    @abstractmethod
    def unwrap(self): pass

    @abstractmethod
    def unwrap_or_default(self, default: Any): pass

    @abstractmethod
    def unwrap_or_call(self, op: Callable[[], Any]): pass

    @abstractmethod
    def unwrap_or_call_with(self, op: Callable[[Any], Any]) -> Any: pass

class Ok(BaseResult[T]):
    def __init__(self, value: T): self.ok_value = value
    def is_ok(self) -> bool: return True
    def unwrap(self) -> T: return self.ok_value
    def unwrap_or_default(self, default: Any = None) -> T: return self.ok_value
    def unwrap_or_call(self, op: Callable[[], Any]) -> T: return self.ok_value
    def unwrap_or_call_with(self, op: Callable[..., Any]) -> Any: return op(self.ok_value)
class Err(BaseResult[E]):
    def __init__(self, value: E): self.err_value = value
    def is_err(self) -> bool: return True
    def unwrap(self) -> NoReturn: raise UnwrapError(ERRORCONSTANTS.UNWRAP_ON_ERR.format(err_value=self.err_value))
    def unwrap_or_default(self, default: Any = None) -> Any: return default
    def unwrap_or_call(self, op: Callable[[], Any]) -> Any: return op()
    def unwrap_err(self) -> E: return self.err_value
    def unwrap_or_call_with(self, op: Callable[..., Any]) -> Any: return op(self.err_value)

class Feedback(BaseResult[F]):
    def __init__(self, value: F): self.feedback_value = value
    def is_feedback(self) -> bool: return True
    def unwrap(self) -> NoReturn: raise UnwrapError(ERRORCONSTANTS.UNWRAP_ON_FEEDBACK.format(feedback_value=self.feedback_value))
    def unwrap_or_default(self, default: Any = None) -> Any: return default
    def unwrap_or_call(self, op: Callable[[], Any]) -> Any: return op()
    def unwrap_feedback(self) -> F: return self.feedback_value
    def unwrap_or_call_with(self, op: Callable[..., Any]) -> Any: return op(self.feedback_value)

ResultType = Union[Ok[T], Err[E], Feedback[F]]

class Result:
    """
    Namespace for Ok, Err, Feedback constructors and type guards for convenient usage: Result.Ok(...), Result.Err(...), Result.Feedback(...), Result.is_ok(...), etc.
    """
    Ok = Ok
    Err = Err
    Feedback = Feedback

    @staticmethod
    def is_ok(obj: ResultType) -> bool:
        return isinstance(obj, Ok)

    @staticmethod
    def is_err(obj: ResultType) -> bool:
        return isinstance(obj, Err)

    @staticmethod
    def is_feedback(obj: ResultType) -> bool:
        return isinstance(obj, Feedback)

    @staticmethod
    def ok(value: T) -> Ok[T]:
        return Ok(value)

    @staticmethod
    def err(value: E) -> Err[E]:
        return Err(value)

    @staticmethod
    def feedback(value: F) -> Feedback[F]:
        return Feedback(value)

    @staticmethod
    def unwrap(obj: ResultType) -> T:
        if Result.is_ok(obj):
            return obj.unwrap()
        elif Result.is_err(obj):
            raise UnwrapError(ERRORCONSTANTS.UNWRAP_ON_ERR.format(err_value=obj.unwrap_err()))
        elif Result.is_feedback(obj):
            raise UnwrapError(ERRORCONSTANTS.UNWRAP_ON_FEEDBACK.format(feedback_value=obj.feedback_value))
        else:
            raise UnwrapError(ERRORCONSTANTS.UNWRAP_ON_UNKNOWN.format(type_name=type(obj).__name__))

    @staticmethod
    def unwrap_or_default(obj: ResultType, default: Any = None) -> Any:
        if Result.is_ok(obj):
            return obj.unwrap()
        return default

    @staticmethod
    def unwrap_or_call(obj: ResultType, op: Callable[[], Any]) -> Any:
        if Result.is_ok(obj):
            return obj.unwrap()
        return op()
