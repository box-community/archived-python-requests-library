from setuptools import setup

setup(name='box-requests',
      version='0.1',
      description='Helper for using Box API with python-requests',
      url='http://github.com/cg2v/box-requests',
      author='Chaskiel Grundman',
      author_email='cg2v@andrew.cmu.edu',
      license='BSD',
      packages=['box_requests'],
      install_requires=['requests'],
      include_package_data=True,
      zip_safe=False)
