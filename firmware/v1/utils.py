import os
import ujson

def load_config(config_file="config.json"):
    config = {}
    if config_file in os.listdir():
        with open(config_file, "r") as f:
            config = ujson.load(f)
    return config

def save_config(config, config_file="config.json"):
    with open(config_file, "w") as f:
        ujson.dump(config, f)
