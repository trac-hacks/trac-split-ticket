import sys
from setuptools import setup

def required_packages():
    """ Return a list of dependencies for the `splitticket` package.

    """
    required = []

    # ensure OrderedDict is available when running under Python < 2.7
    python_version = sys.version_info[:2]

    if python_version < (2, 7):
        required.append('ordereddict')

    return required

setup(name='trac-split-ticket-plugin', version='0.1',
      author='Declan Traynor',
      author_email='dclntrynr@gmail.com',
      url='http://github.com/dclntrynr/trac-split-ticket',
      description='Plugin for Trac 0.11. Extends the ticket workflow so that '
                  'tickets can be marked as split.',
      license='',
      packages=['splitticket', 'splitticket.db'],
      entry_points = {
          'trac.plugins': ['splitticket.env = splitticket.env',
                           'splitticket.workflow = splitticket.workflow',
                           'splitticket.web_ui = splitticket.web_ui']
      },
      package_data = {
          'splitticket': ['templates/*.html', 
                          'htdocs/css/*.css', 
                          'htdocs/js/*.js']
      },
      install_requires=required_packages())