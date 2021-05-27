"""PIP set-up for SKA SDP configuration database package."""

import setuptools

with open("README.md", "r") as file:
    LONG_DESCRIPTION = file.read()

version = {}
with open("src/ska_sdp_config/version.py", "r") as file:
    exec(file.read(), version)  # pylint: disable=exec-used


def requirements_from(fname):
    """Read requirements from a file."""
    with open(fname) as req_file:
        return [req for req in req_file.read().splitlines() if req[0] != "-"]


setuptools.setup(
    name="ska-sdp-config",
    version=version["__version__"],
    description="SKA SDP Configuration Database",
    author="SKA ORCA and Sim Teams",
    license="License :: OSI Approved :: BSD License",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="http://gitlab.com/ska-telescope/sdp/ska-sdp-config/",
    install_requires=requirements_from("requirements.txt"),
    setup_requires=["pytest-runner"],
    tests_require=requirements_from("requirements-test.txt"),
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    scripts=["scripts/ska-sdp"],
    classifiers=[
        "Topic :: Database :: Front-Ends",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Topic :: System :: Distributed Computing",
    ],
)
