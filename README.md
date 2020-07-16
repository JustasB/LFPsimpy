[![Build Status](https://travis-ci.com/JustasB/LFPsimpy.svg?branch=master)](https://travis-ci.com/JustasB/LFPsimpy)
[![codecov](https://codecov.io/gh/JustasB/LFPsimpy/branch/master/graph/badge.svg)](https://codecov.io/gh/JustasB/LFPsimpy)
[![PyPI version](https://badge.fury.io/py/LFPsimpy.svg)](https://badge.fury.io/py/LFPsimpy)

# LFPsimpy: A zero-model-modification, MPI-compatible Python package to compute Local Field Potentials of [NEURON simulator](https://neuron.yale.edu) models

**Zero-modification:** With LFPsimpy, there is no need to modify or re-write a NEURON model to fit a particular pattern or style. Given an existing NEURON model (HOC/Python/cell/network), just add a few Python lines to specify the location and parameters of the LFP electrode. Then run the simulation and plot or further process the LFP signal.

**Python-based:** The package is written in pure Python. Download the Python source code and modify or extend it using a familiar language. A small [.HOC file](https://www.neuron.yale.edu/neuron/static/new_doc/programming/hocsyntax.html) allows plotting the LFP signal using native NEURON graphs.

**Multiple LFP algorithms:** `Line`, `Point`, and `RC` methods of [Parasuram et. al. (2016)]( http://journal.frontiersin.org/article/10.3389/fncom.2016.00065/abstract) are implemented. Extend the Python source code to use a custom algorithm.

**Unlimited electrodes:** Place any number of LFP electrodes in arbitrary 3D locations to simulate multi-electrode arrays.

**MPI-compatible:** The package works with single- and multi-process simulations. Rank 0 contains the electrode values of the whole model.

# Requirements

LFPsimpy requires a working version of NEURON 7.5+ either installed from a [package/installer](https://www.neuron.yale.edu/neuron/download) (easier) or [compiled](https://neurojustas.com/2018/03/27/tutorial-installing-neuron-simulator-with-python-on-ubuntu-linux/) (more challenging). Linux, Mac, and Windows versions are supported.

You must be able to run at least *one* of these commands in a terminal window without errors:
 - `nrniv -python`
 - Or `python -c 'from neuron import h'`

If you cannot run any of these commands, it indicates that there is something amiss with your NEURON installation. Search the error messages on the [NEURON forum](https://www.neuron.yale.edu/phpBB/) for help.

# Installation

Installation depends on how you installed NEURON simulator (installed vs. compiled). 

## If you installed a downloaded NEURON package
Download and extract [this LFPsimpy ZIP file](https://github.com/JustasB/LFPsimpy/archive/master.zip) to a known folder. Then note the location of the `LFPsimpy` sub-folder.

Then append the `LFPsimpy` parent folder location to your `$PYTHONPATH` environmental variable. E.g. `export PYTHONPATH=$PYTHONPATH:/path/to/LFPsimpy-master/`. Place the line in your shell startup file (e.g. `~/.bashrc`) to ensure the variable remains set after an OS restart.

## If you compiled NEURON+Python

To install the library, simply type in `pip install lfpsimpy` in your terminal.


# Usage

To use the library, first load your HOC or Python model in NEURON, insert LFP electrode(s), run simulation, and plot/process the electrode signal.

```
# Load your cell or network model
from neuron import h
run_scripts_build_model_etc()

# Load the LFP library
from LFPsimpy import LfpElectrode

# Place an LFP electrode
# x,y,z in microns
# sampling_period in ms. E.g. 0.1 => 10kHz
# method: either 'Line', 'Point', or 'RC'. See: Parasuram et. al. (2016)
le = LfpElectrode(x=100, y=50, z=0, sampling_period=0.1, method='Line')

# Run the simulation
h.tstop = 100 # <- important!
h.run()

# Plot/process LFP values
le.times   # Contains the sampled LFP times
le.values  # Contains the corresponding sampled LFP voltage values (nV)
```

**More examples** are described in [this Jupyter notebook](https://github.com/JustasB/LFPsimpy/blob/master/examples.ipynb).

# NEURON GUI plotting
When using the NEURON GUI, after the electrode is inserted, you can plot the LFP electrode value with:

`Graph > Current Axis > Plot What? > Objects > LfpElectrode[0].value`
then
`In Tools > RunControl, set Points plotted/ms to 1/sampling_period`

`Init & Run` will show the LFP value of the first inserted electrode

# How It Works
LFPsimpy is a Python re-implementation of [LFPsim](https://github.com/compneuro/LFPsim) described in [Parasuram et. al. (2016)]( http://journal.frontiersin.org/article/10.3389/fncom.2016.00065/abstract). The original publication estimated LFPs using three different methods and also did not require a NEURON model to be in a specific format. However, the original implementation is in HOC, is not MPI-compatible, and places restrictions on the number of electrodes that can be placed in a simulation. 

This library encapsulates the three LFP estimation methods described in the paper and uses the more efficient NEURON's [`i_membrane_`](https://www.neuron.yale.edu/neuron/static/new_doc/simctrl/cvode.html#CVode.use_fast_imem) method. These changes allow arbitrary number of electrodes and allows computing the LFP in MPI-parallelized models.

# Issues
While NEURON allows running simulations past the `tstop` value, this library does not support this usage pattern. If `h.t` exceeds `h.tstop` a warning is shown and the LFP signal is not computed.

If you encounter an issue, first make sure it's not due to NEURON itself. If it is, please contact the [NEURON team](https://www.neuron.yale.edu/phpBB/). If the issue is with this library, please create an [issue on Github](https://github.com/JustasB/LFPsimpy/issues).

# Contributing

To contribute, please open an issue first and discuss your plan for contributing. Then fork this repository and commit a pull-request with your changes.

# Acknowledgements
LFPsimpy is a Python re-implementation of [LFPsim](https://github.com/compneuro/LFPsim) described in [Parasuram et. al. (2016)]( http://journal.frontiersin.org/article/10.3389/fncom.2016.00065/abstract). When using LFPsimpy in research projects, please cite the original publication and this repository, which is maintained by [Justas Birgiolas](https://www.linkedin.com/in/justasbirgiolas).
