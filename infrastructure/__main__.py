import logging
import sys

from infrastructure import SeedDeployment


def main():

    root_logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)-15s - %(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARN)

    logger = logging.getLogger('infrastructure')
    logger.setLevel(logging.INFO)

    seed_deployment = SeedDeployment()
    seed_deployment.deploy()


if __name__ == '__main__':
    main()
