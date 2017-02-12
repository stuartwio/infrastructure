import hudson.plugins.git.BranchSpec
import hudson.plugins.git.GitSCM
import hudson.plugins.git.UserRemoteConfig
import hudson.triggers.SCMTrigger
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def jenkins = Jenkins.instance
def host = System.properties.getProperty('git.host', 'git')

if (!jenkins.jobNames.find { jobName -> jobName == "seed" }) {

    def job = jenkins.createProject(WorkflowJob, 'seed')
    job.addTrigger(new SCMTrigger('H/2 * * * *'))
    def remote = new UserRemoteConfig("git@${host}:seed.git", null, null, 'git')
    def scm = new GitSCM(
            [remote] as List, [new BranchSpec("*/master")],
            false, [], null, null, [])
    def definition = new CpsScmFlowDefinition(scm, 'Jenkinsfile')

    job.setDefinition(definition)
    jenkins.save()
}
