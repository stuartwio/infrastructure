import hudson.FilePath
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import jenkins.model.Jenkins
import jenkins.security.s2m.AdminWhitelistRule

/**
 * Generates a password.
 * @return the generated password
 */
static generatePassword() {
    UUID.randomUUID()
        .toString()
        .replace('-', '')
        .toLowerCase(Locale.ENGLISH)
}

/**
 * Loads the password from the file system if
 * it exists or generates it if it doesn't.
 * @param path of the password file on the file system
 * @return the password
 */
static loadPassword(FilePath path) {
    if (path.exists()) {
        return path.readToString()
    }
    return generatePassword()
}

/**
 * Saves the password to the file system only
 * if the path does not exist.
 * @param path of the password file on the file system
 * @param password the password to save
 */
static savePassword(FilePath path, String password) {
    if (!path.exists()) {
        path.touch(System.currentTimeMillis())
        path.chmod(0600)
        new File(path.absolutize() as String).withWriter {
            it << password
        }
    }
}

def jenkins = Jenkins.instance

/* Get the path of the password file */
def path = jenkins.getRootPath().child('secrets/adminPassword')

/* Create the admin user */
def username = 'admin'
def password = loadPassword(path)
def description = 'Administrator'
def realm = new HudsonPrivateSecurityRealm(false)
def account = realm.createAccount(username, password)
account.setDescription(description)
jenkins.setSecurityRealm(realm)

/* Disable anonymous read access */
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.allowAnonymousRead = false
jenkins.setAuthorizationStrategy(strategy)

jenkins.injector.getInstance(AdminWhitelistRule.class)
    .setMasterKillSwitch(false)

/* Save the configuration to the file system */
jenkins.save()
savePassword(path, password)
