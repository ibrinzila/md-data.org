import logging
from dataclasses import dataclass


@dataclass
class BaseWorker:
    name: str = "base"

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(self.name)

    def log(self, message: str) -> None:
        self.logger.info(message)

