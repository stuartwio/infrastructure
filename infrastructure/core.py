import logging


class Spec(object):

    def apply(self, conn):
        raise NotImplementedError("fetch not implemented")


class ResourceSpec(Spec):

    _logger = logging.getLogger(__name__)

    def apply(self, conn):
        self._logger.info("Checking if {} resource exist...".format(self.__class__.__name__))
        resource = self.fetch(conn)
        if resource is None:
            self._logger.info("{} resource does not exist! Creating resource...".format(self.__class__.__name__))
            resource = self.create(conn)
            self._logger.info("{} resource created!".format(self.__class__.__name__))
        else:
            self._logger.info("{} resource exists!".format(self.__class__.__name__))
        return resource

    def fetch(self, conn):
        raise NotImplementedError("fetch not implemented")

    def create(self, conn):
        raise NotImplementedError("create not implemented")


class Resource(object):

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.__dict__)
