import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.model.Jenkins
import jenkins.security.s2m.AdminWhitelistRule

def username = 'admin'

def password = UUID.randomUUID().toString().replace("-", "").toLowerCase(Locale.ENGLISH)

println("--------------------------------------------------")
println(password)
println("--------------------------------------------------")

def description = 'Administrator'

def jenkins = Jenkins.instance

def hudsonRealm = new HudsonPrivateSecurityRealm(false)

def user = hudsonRealm.createAccount(username, password)

user.setDescription(description)

jenkins.setSecurityRealm(hudsonRealm)

jenkins.save()

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()

strategy.allowAnonymousRead = true

jenkins.setAuthorizationStrategy(strategy)

def filePath = jenkins.getRootPath().child('secrets/adminPassword')

filePath.touch(System.currentTimeMillis())

filePath.chmod(0600)

jenkins.injector.getInstance(AdminWhitelistRule.class)
        .setMasterKillSwitch(false)

jenkins.save()

def file = new File(filePath.absolutize() as String)

file << password
