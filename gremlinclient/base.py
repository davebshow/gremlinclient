from abc import ABCMeta, abstractmethod, abstractproperty
from six import add_metaclass


@add_metaclass(ABCMeta)
class AbstractBaseFactory(object):

    @abstractmethod
    def connect(cls):
        pass


@add_metaclass(ABCMeta)
class AbstractBaseResponse(object):

    @abstractmethod
    def send(self):
        pass

    @abstractmethod
    def receive(self):
        pass


@add_metaclass(ABCMeta)
class AbstractBaseConnection(object):

    @abstractmethod
    def submit(self):
        pass

    @abstractproperty
    def closed(self):
        pass
