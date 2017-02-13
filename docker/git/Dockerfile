FROM alpine

RUN apk update && apk add openssh git && \
    addgroup -g 1001 git && \
    adduser -h /home/git -s /bin/sh -D -G git -u 1001 git

EXPOSE 22

VOLUME /etc/ssh
VOLUME /home/git

USER sshd

CMD ["/usr/sbin/sshd", "-D"]
