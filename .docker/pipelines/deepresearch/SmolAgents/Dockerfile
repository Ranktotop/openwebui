# Use the existing Pipelines image as the base image
FROM ghcr.io/open-webui/pipelines:main

# Set the working directory
WORKDIR /app

#clone repo and place scripts in /app/scripts and copy requirements.txt
# repo: https://github.com/elabbarw/aiagent_playground.git
# subfolder: openwebui/pipelines/deepresearch/scripts
RUN git clone https://github.com/elabbarw/aiagent_playground.git && \
    mkdir -p /app/scripts && \
    cp -r aiagent_playground/openwebui/pipelines/deepresearch/scripts/* /app/scripts/ && \
    cp aiagent_playground/openwebui/pipelines/deepresearch/requirements.txt /app/ && \
    rm -rf aiagent_playground

# Install Python dependencies
RUN pip install -r requirements.txt