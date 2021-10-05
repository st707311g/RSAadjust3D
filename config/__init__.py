import json
import os

application_name = 'RSAadjust3D'
description = "a position adjustment software for PET-CT RSA data"
version = 0
revision = 1

skip_size = 2

def version_string():
    return f'{version}.{revision}'

def parse_version_string(version_string):
    return [int(i) for i in version_string.split(sep='.')]

config_dir = os.path.dirname(__file__)
config_file = os.path.join(config_dir, 'config.json')

params = {}
