from openstack import connection, exceptions
import yaml
import os.path


class ResourceSpec(object):

    def apply(self, conn):
        resource = self.fetch(conn)
        if resource is None:
            resource = self.create(conn)
        return resource

    def fetch(self, conn):
        raise NotImplementedError("fetch not implemented")

    def create(self, conn):
        raise NotImplementedError("create not implemented")


def first(gen):
    try:
        return next(gen)
    except StopIteration:
        return None


class ExternalNetworkSpec(ResourceSpec):

    def fetch(self, conn):
        return first(conn.network.networks(name='ext-net'))

    def create(self, conn):
        raise ValueError("cannot create ext-net")


class DevelopmentNetworkSpec(ResourceSpec):

    def fetch(self, conn):
        return first(conn.network.networks(name='stuartwio-development-network'))

    def create(self, conn):
        return conn.network.create_network(
            name='stuartwio-development-network'
        )


class DevelopmentSubnetSpec(ResourceSpec):

    _cidr = dict(
        a='10.0.1.0/24',
        b='10.0.2.0/24',
        c='10.0.3.0/24'
    )

    _gateway_id = dict(
        a='10.0.1.1',
        b='10.0.2.1',
        c='10.0.3.1'
    )

    def __init__(self, suffix):
        self._suffix = suffix
        self._network_spec = DevelopmentNetworkSpec()
        self._router_spec = DevelopmentRouterSpec()

    def fetch(self, conn):
        return first(conn.network.subnets(name='stuartwio-development-subnet-{}'.format(self._suffix)))

    def create(self, conn):
        network = self._network_spec.apply(conn)
        router = self._router_spec.apply(conn)
        subnet = conn.network.create_subnet(
            name='stuartwio-development-subnet-{}'.format(self._suffix),
            network_id=network.id,
            ip_version='4',
            cidr=self._cidr[self._suffix],
            gateway_id=self._cidr[self._suffix]
        )
        conn.network.add_interface_to_router(router, subnet.id)
        return subnet


class DevelopmentRouterSpec(ResourceSpec):

    def __init__(self):
        self._external_network_spec = ExternalNetworkSpec()

    def fetch(self, conn):
        return first(conn.network.routers(name='stuartwio-development-router'))

    def create(self, conn):
        return conn.network.create_router(
            name='stuartwio-development-router',
            external_gateway_info=dict(
                network_id=self._external_network_spec.apply(conn).id
            )
        )


class DevelopmentNetworkStackSpec(ResourceSpec):

    def __init__(self):
        self._network_spec = DevelopmentNetworkSpec()
        self._router_spec = DevelopmentRouterSpec()
        self._subnet_a_spec = DevelopmentSubnetSpec('a')
        self._subnet_b_spec = DevelopmentSubnetSpec('b')
        self._subnet_c_spec = DevelopmentSubnetSpec('c')

    def fetch(self, conn):
        return DevelopmentNetworkStackResource(
            network=self._network_spec.apply(conn),
            router=self._router_spec.apply(conn),
            subnet_a=self._subnet_a_spec.apply(conn),
            subnet_b=self._subnet_b_spec.apply(conn),
            subnet_c=self._subnet_c_spec.apply(conn)
        )

    def create(self, conn):
        raise ValueError('cannot create infrastructure directly')


class DevelopmentNetworkStackResource(object):

    def __init__(self, network, router, subnet_a, subnet_b, subnet_c):
        self.network = network
        self.router = router
        self.subnet_a = subnet_a
        self.subnet_b = subnet_b
        self.subnet_c = subnet_c


class DevelopmentServerKeyPairSpec(ResourceSpec):

    def fetch(self, conn):
        try:
            return conn.compute.get_keypair('stuartwiodev')
        except exceptions.ResourceNotFound:
            return None

    def create(self, conn):
        key_pair = conn.compute.create_keypair(name='stuartwiodev')

        with open(os.path.join(os.getcwd(), 'stuartwiodev.pub'), 'w') as f:
            f.write(key_pair.public_key)

        with open(os.path.join(os.getcwd(), 'stuartwiodev.pem'), 'w') as f:
            f.write(key_pair.private_key)

        return key_pair


class DevelopmentServerSpec(ResourceSpec):

    def fetch(self, conn):
        raise NotImplementedError()

    def create(self, conn):
        raise NotImplementedError()


def readconfig():
    with open(os.path.join(os.path.expanduser('~'), '.stuartwio', 'infrastructure.yaml')) as f:
        return yaml.load(f.read())

def main():

    config = readconfig()
    conn = connection.from_config(config['citycloud']['cloud_name'])

    # flavors = [flavor
    #            for flavor in conn.compute.flavors()
    #            if flavor.vcpus == 2
    #            and 4000 < flavor.ram < 5000
    #            and flavor.disk == 50]
    #
    # for flavor in flavors:
    #     print(flavor)

    # print(conn.compute.find_flavor('2C-4GB-50GB'))
    # print(conn.compute.find_image('CoreOS 1068.9.0'))
    #
    # network_stack = DevelopmentNetworkStackSpec().apply(conn)
    #
    # print(network_stack.network.id)

    conn.compute.delete_keypair('stuartwiodev')

    key_pair = DevelopmentServerKeyPairSpec().apply(conn)

    # {
    #     "keypair": {
    #         "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCtu4JW4X7a8rqqqt379+uLo97Blc4qCT9W82D55wH3IgNEOz1yzF+La6MUAsyq6RD6QNcgOcC4+PIvSZMPvT2BINYava/ViH+v4mnQ44qr91SiBn/g7AnDPYVr6MprY9H9nAyhGNSlvcbK264gQFeJVKYhKlWa9poTtVN7KSoUQhjEMQ8NPb1x56pXyur7Ug2DgMXU7r6n/fhl63dC9IYvlYMUggIB5dPR4FEoVWn77Lp401qjWQpEBc28v7tXwTYrQQowyE9vKx6OmZ+MKbpv5A9t11kxMVXX6AB/oA3m5SfoCP5vcW9E+Z4s36RpmLB7j9zO97yauHgQtiO4zmjB Generated-by-Nova",
    #         "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEqAIBAAKCAQEArbuCVuF+2vK6qqrd+/fri6PewZXOKgk/VvNg+ecB9yIDRDs9\ncsxfi2ujFALMqukQ+kDXIDnAuPjyL0mTD709gSDWGr2v1Yh/r+Jp0OOKq/dUogZ/\n4OwJwz2Fa+jKa2PR/ZwMoRjUpb3GytuuIEBXiVSmISpVmvaaE7VTeykqFEIYxDEP\nDT29ceeqV8rq+1INg4DF1O6+p/34Zet3QvSGL5WDFIICAeXT0eBRKFVp++y6eNNa\no1kKRAXNvL+7V8E2K0EKMMhPbysejpmfjCm6b+QPbddZMTFV1+gAf6AN5uUn6Aj+\nb3FvRPmeLN+kaZiwe4/czve8mrh4ELYjuM5owQIDAQABAoIBAGoNWqU6hbuWDIj+\nQP/8+VaGtAYsMmvKtVWYwAwNDlAT/TZ7iyk2xORQ0n32r4VtPKXnSusrFhBUN1LS\ncOlctdzLdKdiP6Hz7y4o4jtXi2EqXAmEOi/NJrB+L6INuvMPPjK4PaVhiP2b+Wv/\n6i1Z2ZXFjJwWQaeU/b0mJU27dSpjorIHwEIBabGEnKdkVWt6f/AeHd/S1OU3oKL8\nUOjMlcyPLf1PivZ/TBBGXZbA8lW2AAmfXCeBoUabEE3G8WOWCUTNe50AZqS2lnrl\nVa4mMDQMMLt0vRwNg+H0CCSk/ednXBze23p/eR+1oYK1CsPVZp9eS4nN+d4kmIFN\nq8emLiECggCBALby8ZexqNRzfD7Z1reyB+ULkY72mVhhqOoiPRM3IjiL9q4Nnp3Y\n2f8Rg4FZTFVMAfGoGVF1u5+MrmAwH5XCZuB4H6nXG1K+GZG6/Xqwp/UDKJm1Tq17\nqZrBeVg3xpuFH6tfg6GBUl1tZRUnawTQAVNs5FhhTrpMeu7HEs1JM9y9AoIAgQDz\nGnM4Rw5AKxvKBMM3hg4z6zgcvDWavx3/0wA1qKcELwLIGQNpCUEN//3qNDn5rdQy\niu4JL3jVvrlNRGXlMWDBAZp4GbX5PeqVyd8tN8gr0hctvydjj66puVo0lOmEhu3Q\n+To5Jp5pu1R8X+iqwRkOa8Uoql1WB6fvdJMQeSN2VQKCAIBBVJIXVHbwnujQXOQD\nJw0Qqsfo4IC0AfPa4C0lLnwG61xEnVJ2FZkLL8rhJu1OTF0pWZjo8Pz2JbujV6v/\nw7MPF3ZfJRR5wK7KzpZz+J+Rq/YUpZ0Z8F4JiGt3qDtBEBHWFb6grtilykndev0J\nc+n1S55jPSRq/KKtn+ND8Y8WlQKCAIEAuABZHUuK2b7HNc0NBUWOEnYC7pz15b6q\nMiu+iN6yK1R5woJMNoAuoS4VPeNxzi1n4ymMqZ8o0n+dOYJ/rU4GcY+JH0Y2mgPn\nPqChL1R9Sc2mhZWddpoWFZiZUhsz9H88GWPKUd+NH3IOrGTbcgLduDCR9gmcw7Tf\nwzp05Y8K7FECggCAUhFNTLGmQeSsERolyf0AHexWYGHUMOSJq2VORWhH4tXUONIx\ndrnnM9CJdCPE47UmIpWHkRkrd7WrViv4dMsMpMgvzb4+RcGlEk418ebXa/lnOI2z\nnbYnVSCpYzZHzMFwULmdLVLTmVgTFkPOLZ7LRq3jve9Or6gb7SXQUmfrjxY=\n-----END RSA PRIVATE KEY-----\n",
    #         "user_id": "62b3d579fb134b428a3fc1b3453219f5",
    #         "name": "testkeypair",
    #         "fingerprint": "28:86:fe:48:a0:c0:13:6e:8b:e0:b4:e7:45:e1:a0:a5"
    #     }
    # }


if __name__ == '__main__':
    main()
