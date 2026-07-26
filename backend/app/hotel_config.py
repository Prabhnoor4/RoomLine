import json

from app import config

# We only want to read and parse the JSON file once, not every time
# load_hotel_config() is called. This variable stores the result after
# the first call so later calls can just reuse it.
_cached_config = None


def load_hotel_config():
    global _cached_config

    if _cached_config is None:
        with open(config.HOTEL_CONFIG_PATH) as f:
            _cached_config = json.load(f)

    return _cached_config
