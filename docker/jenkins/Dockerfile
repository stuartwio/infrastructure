FROM jenkins:alpine

USER root

COPY plugins.txt /usr/share/jenkins/plugins.txt

RUN cat /usr/share/jenkins/plugins.txt | xargs /usr/local/bin/install-plugins.sh

COPY init.groovy.d /usr/share/jenkins/ref/init.groovy.d

RUN chown -R jenkins:jenkins /usr/share/jenkins/ref

USER jenkins
