from setuptools import setup, find_packages
import subprocess
import sys

# Install dependencies
subprocess.call([sys.executable, "-m", "pip", "install", 'slackclient'])

MAIN_MODULE = 'agent'

# Find the agent package that contains the main module
packages = find_packages('.')
agent_package = 'slack_health'

# Find the version number from the main module
agent_module = agent_package + '.' + MAIN_MODULE
_temp = __import__(agent_module, globals(), locals(), ['__version__'], -1)
__version__ = _temp.__version__

# Setup
setup(
    name=agent_package + 'agent',
    version=__version__,
    author_email="tnesztler@ecorithm.com",
    url="https://ecorithm.com",
    description="Reports health of configured agents to Slack channels",
    author="Thibaud Nesztler",
    install_requires=['volttron', 'slackclient'],
    packages=packages,
    entry_points={
        'setuptools.installation': [
            'eggsecutable = ' + agent_module + ':main',
        ]
    }
)
