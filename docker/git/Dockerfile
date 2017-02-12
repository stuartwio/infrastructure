FROM alpine

RUN apk update && apk add openssh git && \
    addgroup -g 1001 git && \
    adduser -h /home/git -s /bin/sh -D -G git -u 1001 git

RUN \
    sed -i 's/#\?PasswordAuthentication\b.*/PasswordAuthentication no/' \
        /etc/ssh/sshd_config && \
    sed -i 's/#\?ChallengeResponseAuthentication\b.*/ChallengeResponseAuthentication no/' \
        /etc/ssh/sshd_config && \
    sed -i 's/#\?PermitRootLogin\b.*$/PermitRootLogin no/' \
        /etc/ssh/sshd_config

COPY entrypoint.sh /

EXPOSE 22

VOLUME /home/git

USER git

CMD ["/entrypoint.sh"]
