#!/usr/bin/with-contenv bashio
set -e
set +u
set +o nounset

ADVERTISED_IP=$(bashio::config 'advertised_ip')
SERVER_IP="0.0.0.0" # TODO: Make it only open to home-assistant, not to the whole network
SERVER_PORT=$(bashio::config 'server_port')
MONITOR_POLL_INTERVAL=$(bashio::config 'monitor_poll_interval')
LOG_LEVEL=$(bashio::config 'log_level')
CONFIG_PATH=/data/conf.json

normalized_log_level="${LOG_LEVEL,,}"

case "${normalized_log_level}" in
    debug | info | warn | warning | error)
        ;;
    *)
        bashio::log.warning "Unknown log level '${LOG_LEVEL}', defaulting to info."
        normalized_log_level="info"
        LOG_LEVEL="info"
        ;;
esac

log_with_level() {
    local message="${1}"
    case "${normalized_log_level}" in
        debug)
            bashio::log.debug "${message}"
            ;;
        warn | warning)
            bashio::log.warning "${message}"
            ;;
        error)
            bashio::log.error "${message}"
            ;;
        *)
            bashio::log.info "${message}"
            ;;
    esac
}

export MONITOR_POLL_INTERVAL
export LOG_LEVEL

if ! bashio::config.has_value 'advertised_ip'; then
    bashio::log.info "No advertised_ip configured, auto-detecting..."
    IPV4_ADDRESS=$(bashio::network.ipv4_address)
    ADVERTISED_IP="${IPV4_ADDRESS%/*}"
else
    bashio::log.info "Using configured advertised_ip: ${ADVERTISED_IP}"
fi

PYTHON_VERSION="$(/opt/venv/bin/python --version 2>&1 || true)"
log_with_level "Python runtime: ${PYTHON_VERSION}"
log_with_level "Starting Cremalink local server on ${SERVER_IP}:${SERVER_PORT} (monitor poll: ${MONITOR_POLL_INTERVAL}s, log level: ${LOG_LEVEL})"

exec /opt/venv/bin/cremalink-server --ip "${SERVER_IP}" --port "${SERVER_PORT}" --advertised_ip "${ADVERTISED_IP}" --settings_path "${CONFIG_PATH}"
