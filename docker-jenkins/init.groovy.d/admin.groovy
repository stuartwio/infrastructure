import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.model.Jenkins
import jenkins.security.s2m.AdminWhitelistRule

def jenkins = Jenkins.instance

def filePath = jenkins.getRootPath().child('secrets/adminPassword')

def username = 'admin'
def password = (filePath.exists()) ? filePath.readToString() :
    UUID.randomUUID().toString().replace("-", "").toLowerCase(Locale.ENGLISH)
def description = 'Administrator'

def hudsonRealm = new HudsonPrivateSecurityRealm(false)

def user = hudsonRealm.createAccount(username, password)
user.setDescription(description)

jenkins.setSecurityRealm(hudsonRealm)

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.allowAnonymousRead = false
jenkins.setAuthorizationStrategy(strategy)

jenkins.injector.getInstance(AdminWhitelistRule.class)
        .setMasterKillSwitch(false)

jenkins.save()

if (!filePath.exists()) {
    filePath.touch(System.currentTimeMillis())
    filePath.chmod(0600)
    new File(filePath.absolutize() as String).withWriter {
        it << password
    }
}