from distutils.core import setup

setup(
    name='cherry-common',
    version='0.2.6a',
    packages=['cherrycommon'],
    url='',
    license='MIT',
    author='WYSEGames',
    author_email='info@wysegames.com',
    description='Set of various utilities used by cherry game engine.',
    install_requires=[
        "tornado >= 2.4",
        "pymongo >= 2.3",
        "xlwt",
        "xlrd",
        "python-daemon"
    ],
    extras_require={
        'AMF data encode/decode':  ['pyamf'],
        'YAML data encode/decode': ['pyyaml']
    }
)
