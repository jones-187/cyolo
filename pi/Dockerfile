FROM node:24-bookworm

ARG HOST_USER=developer
ARG HOST_UID=1000
ARG HOST_GID=1000
ARG HOST_HOME=/home/developer
ARG PI_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git openssh-client python3 python3-pip python3-venv sudo jq ripgrep \
    && rm -rf /var/lib/apt/lists/*

RUN if getent group "${HOST_GID}" >/dev/null; then \
        previous_group=$(getent group "${HOST_GID}" | cut -d: -f1); \
        if [ "${previous_group}" != "${HOST_USER}" ]; then groupmod -n "${HOST_USER}" "${previous_group}"; fi; \
    else groupadd -g "${HOST_GID}" "${HOST_USER}"; fi \
    && if getent passwd "${HOST_UID}" >/dev/null; then \
        previous_user=$(getent passwd "${HOST_UID}" | cut -d: -f1); \
        if [ "${previous_user}" != "${HOST_USER}" ]; then usermod -l "${HOST_USER}" "${previous_user}"; fi; \
        usermod -d "${HOST_HOME}" -m -g "${HOST_GID}" -s /bin/bash "${HOST_USER}"; \
    else useradd -m -d "${HOST_HOME}" -u "${HOST_UID}" -g "${HOST_GID}" -s /bin/bash "${HOST_USER}"; fi \
    && mkdir -p "${HOST_HOME}/.cache/uv" \
    && chown -R "${HOST_UID}:${HOST_GID}" "${HOST_HOME}" \
    && printf '%s ALL=(ALL) NOPASSWD:ALL\n' "${HOST_USER}" > /etc/sudoers.d/pi-yolo \
    && chmod 0440 /etc/sudoers.d/pi-yolo

ENV UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_DOWNLOADS=never

RUN test -n "${PI_VERSION}" \
    && npm install --global "@earendil-works/pi-coding-agent@${PI_VERSION}" \
    && python3 -m pip install --break-system-packages 'PyYAML>=5.4' 'sqlglot>=24.0' 'PyMySQL>=1.1' uv \
    && uv tool install --python /usr/bin/python3 mcp-grafana \
    && uvx --offline --python /usr/bin/python3 mcp-grafana --help >/dev/null \
    && git config --system core.quotepath false \
    && git config --system core.editor vim

ENV HOME=${HOST_HOME} \
    USER=${HOST_USER} \
    LOGNAME=${HOST_USER} \
    JAVA_HOME=/opt/java \
    MAVEN_HOME=/opt/maven \
    UV_CACHE_DIR=${HOST_HOME}/.cache/uv \
    PATH=/opt/maven/bin:/opt/java/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

USER ${HOST_USER}
WORKDIR /tmp
CMD ["sleep", "infinity"]
