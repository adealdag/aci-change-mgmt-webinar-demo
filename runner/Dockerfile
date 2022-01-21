FROM centos:8.4.2105

# Create user
RUN useradd -G root -ms /bin/bash runner
WORKDIR /home/runner

# Create folder
RUN mkdir actions-runner
WORKDIR /home/runner/actions-runner

# Download the latest runner package
RUN curl -o actions-runner-linux-x64-2.286.1.tar.gz -L https://github.com/actions/runner/releases/download/v2.286.1/actions-runner-linux-x64-2.286.1.tar.gz
# Optional: Validate the hash
# RUN echo "7b1509c353ea4e6561b2ed2e916dcbf2a0d8ce21172edd9f8c846a20b6462cd6  actions-runner-linux-x64-2.286.1.tar.gz" | shasum -a 256 -c
# Extract the installer
RUN tar xzf ./actions-runner-linux-x64-2.286.1.tar.gz

# Install dependencies
RUN ./bin/installdependencies.sh

# We need docker in docker

USER runner

ENTRYPOINT []