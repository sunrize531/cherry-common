from distutils.core import setup

setup(
    name='cherry-forms',
    version='0.1a',
    packages=['cherrycommon'],
    url='',
    license='MIT',
    author='WYSEGames',
    author_email='info@wysegames.com',
    description='Set of UIModules for building forms with Tornado web server. Widgets also can be used as standalone on clientside.',
    install_requires=[
        "tornado >= 2.4",
        "pymongo >= 2.3"
    ],
)
