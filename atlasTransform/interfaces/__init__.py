
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:

# Load modules for compatibility
from niworkflows.interfaces import (
    bids, utils)

from .reports import SubjectSummary, AboutSummary
from .atlasTransform import AtlasTransform


class DerivativesDataSink(bids.DerivativesDataSink):
    out_path_base = __name__.split('.')[0]


__all__ = [
    'bids',
    'utils',
    'SubjectSummary',
    'AboutSummary',
    'DerivativesDataSink',
    'AtlasTransform'
]