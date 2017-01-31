import hudson.plugins.git.BranchSpec
import hudson.plugins.git.GitSCM
import hudson.plugins.git.UserRemoteConfig
import hudson.triggers.SCMTrigger
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def job = Jenkins.instance.createProject(WorkflowJob, 'seed')

job.addTrigger(new SCMTrigger('H/2 * * * *'))

def remote = new UserRemoteConfig('git@localhost:seed.git', null, null, 'jenkins-git')

def scm = new GitSCM(
        Collections.singletonList(remote),
        Collections.singletonList(new BranchSpec("*/master")),
        false,
        Collections.emptyList(),
        null, null, Collections.emptyList())

def definition = new CpsScmFlowDefinition(scm, 'Jenkinsfile')

job.setDefinition(definition)


