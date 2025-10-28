from setuptools import setup

setup(name='cbpi4-hendictrl',
      version='0.0.1',
      description='Hendi Control',
      author='Matthias Hansen',
      author_email='cbpi4@hopfenhuhn.de',
      url='https://github.com/hopfenhuhn/cbpi4-hendictrl.git',
      include_package_data=True,
      package_data={
        # If any package contains *.txt or *.rst files, include them:
      '': ['*.txt', '*.rst', '*.yaml'],
      'cbpi4-hendictrl': ['*','*.txt', '*.rst', '*.yaml']},
      packages=['cbpi4-hendictrl'],
     )
