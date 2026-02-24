from abc import ABC, abstractmethod


class LoggerService(ABC):

    @abstractmethod
    def log(self, message: str) -> None:
        """
        Logs a message.
        """
        pass