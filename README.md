# FRAPalyzer
[![Build Status](https://travis-ci.org/rbnvrw/FRAPalyzer.svg?branch=master)](https://travis-ci.org/rbnvrw/FRAPalyzer)
[![Code Climate](https://codeclimate.com/github/rbnvrw/FRAPalyzer/badges/gpa.svg)](https://codeclimate.com/github/rbnvrw/FRAPalyzer)
[![Test Coverage](https://codeclimate.com/github/rbnvrw/FRAPalyzer/badges/coverage.svg)](https://codeclimate.com/github/rbnvrw/FRAPalyzer/coverage)

Analyze Nikon ND2 stimulation FRAP experiments automatically

**Important**: this package requires a special version of [nd2reader](https://github.com/rbnvrw/nd2reader) to be installed.

It currently supports circular and rectangular ROIs and assumes the presence of a reference ROI, a stimulation ROI and a background ROI.
At the moment, it also assumes an ND experiment with a pre-bleach scan, followed by a bleach step and a post-bleach scan. More features will be added regularly.
If you require a specific feature, please open an issue. Pull requests are very welcome.
