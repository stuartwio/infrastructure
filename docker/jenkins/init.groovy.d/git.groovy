import com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.plugins.credentials.common.IdCredentials

def scope = CredentialsScope.GLOBAL

/* Create git SSH key credentials */
def id = 'git'
def username = 'git'
def source = new BasicSSHUserPrivateKey.UsersPrivateKeySource()
def passphrase = null
def description = 'SSH key for Jenkins access to Git repository.'
def ssh = new BasicSSHUserPrivateKey(
        scope, id, username, source, passphrase,
        description)

def provider = SystemCredentialsProvider.instance
def credentials = provider.credentials

def match = credentials.find {
    (it instanceof IdCredentials) &&
        (it as IdCredentials).id == id
}

if (!match) {
    credentials.add(ssh)
    provider.save()
}
