"""PIP set-up for SKA SDP configuration database package."""

import setuptools

with open('README.md', 'r') as file:
    LONG_DESCRIPTION = file.read()

version = {}
with open('src/ska_sdp_config/version.py', 'r') as file:
    exec(file.read(), version) # pylint: disable=exec-used

with open('requirements.txt') as f:
    requirements = f.read().splitlines()
with open('requirements-test.txt') as f:
    requirements_test = f.read().splitlines()

setuptools.setup(
    name='ska-sdp-config',
    version=version['__version__'],
    description='SKA SDP Configuration Database',
    author='SKA ORCA and Sim Teams',
    license='License :: OSI Approved :: BSD License',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='http://gitlab.com/ska-telescope/sdp-config/',
    install_requires=requirements,
    setup_requires=['pytest-runner'],
    tests_require=requirements_test,
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    scripts=['scripts/sdpcfg'],
    classifiers=[
        'Topic :: Database :: Front-Ends',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: System :: Distributed Computing',
    ]
)
