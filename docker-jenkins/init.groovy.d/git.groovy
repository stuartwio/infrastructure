import com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.domains.Domain
import com.cloudbees.plugins.credentials.SystemCredentialsProvider

// TODO: First check if credentials exist as this is run every time Jenkins starts

def scope = CredentialsScope.GLOBAL

def id = 'jenkins-git'
def username = 'git'
def source = new BasicSSHUserPrivateKey.UsersPrivateKeySource()
def passphrase = null
def description = 'SSH key for Jenkins access to Git repository.'

def ssh = new BasicSSHUserPrivateKey(
        scope, id, username, source, passphrase,
        description)

def provider = SystemCredentialsProvider.instance

provider.domainCredentialsMap[Domain.global()].add(ssh)
provider.save()
