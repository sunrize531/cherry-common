__author__ = 'sunrize'
import yaml


def dumps(data):
    return yaml.safe_dump(data)


def loads(data):
    return yaml.parse(data)