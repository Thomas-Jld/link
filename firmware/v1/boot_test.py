from net import connect_to_wifi, host_config_server
from utils import load_config

# Load config.json
config = load_config()

# Connect to wifi
if not connect_to_wifi(config):
    # If not connected to wifi, create an access point
    host_config_server(config)
