from abc import ABC, abstractmethod


class MovementBackend(ABC):
    @abstractmethod
    def start(self, config):
        raise NotImplementedError

    @abstractmethod
    def send_movement(self, movement):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError