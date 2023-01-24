#!/bin/sh

mkdir -p ~/junit
python -m pytest $PYTEST_COMMON_OPTIONS

#python -m pytest $PYTEST_COMMON_OPTIONS --splits 2 --group 1 --splitting-algorithm least_duration &
#python -m pytest $PYTEST_COMMON_OPTIONS --splits 2 --group 2 --splitting-algorithm least_duration
