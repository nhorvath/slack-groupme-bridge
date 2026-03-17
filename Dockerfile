FROM --platform=linux/amd64 ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    make \
    libgmp-dev \
    libffi-dev \
    zlib1g-dev \
    xz-utils \
    gnupg \
    git \
    ca-certificates

RUN curl -fsSL https://github.com/commercialhaskell/stack/releases/download/v2.15.3/stack-2.15.3-linux-x86_64.tar.gz \
    | tar xz -C /usr/local/bin --strip-components=1 --wildcards '*/stack' \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY stack.yaml slack-groupme-bridge.cabal ./
RUN stack setup --no-terminal
RUN stack build --only-dependencies --no-terminal

COPY . .
RUN stack build --no-terminal
RUN cp $(stack path --dist-dir)/build/slack-groupme-bridge-exe/slack-groupme-bridge-exe /slack-groupme-bridge-exe


FROM --platform=linux/amd64 ubuntu:20.04

RUN apt-get update && apt-get install -y libgmp-dev netbase ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /slack-groupme-bridge-exe /bin/slack-groupme-bridge-exe

EXPOSE 5000

WORKDIR /var/local/
ENTRYPOINT ["slack-groupme-bridge-exe"]
