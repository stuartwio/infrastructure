# Infrastructure

TODO...

## Contents

- [Setup](#setup)
- [Testing](#testing)
- [Deployment](#deployment)
- [Sharing](#sharing)
- [Contributing](#contributing)

## Setup

TODO...

## Testing

TODO...

## Deployment

TODO...

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m infrastructure
```

```bash
ssh -i seed.pem core@x.x.x.x sudo su git -c '\
    /bin/bash -c "\
        /usr/bin/cat >> ~/.ssh/authorized_keys"' < ~/.ssh/id_rsa.pub
ssh -i seed.pem core@x.x.x.x sudo su git -c '\
    /bin/bash -c "\
        /usr/bin/cat ~/.ssh/authorized_keys"'
```

Now you have access to the `git` user on the server and can create
some git repositories:

```bash
ssh git@x.x.x.x git init --bare my-project/my-repo.git
```

To add Jenkins jobs, checkout the seed repository, which will already
exist but is empty:

```bash
git clone git@x.x.x.x:seed.git
```

Add a `Jenkinsfile` and point to your remote jobs.

## Sharing

TODO...

## Contributing

TODO...
