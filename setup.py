import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="LFPsimpy",
    version="0.1.1",
    author="Justas Birgiolas",
    author_email="justas@asu.edu",
    description="Zero-model-modification, MPI-compatible Python package for "
                "computing NEURON simulator model local field potentials (LFPs)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/justasb/LFPsimpy",
    packages=setuptools.find_packages(),
    package_data = {
        'LFPsimpy': ['LFPsimpy.hoc'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)