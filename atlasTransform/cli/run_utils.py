import os
from pathlib import Path
import logging
import sys
import gc
import warnings
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter
from ..utils.atlas import CRADDOCK_CLUSTER_SIZES


def _warn_redirect(message, category, filename, lineno, logger, file=None, line=None):
    logger.warning('Captured warning (%s): %s', category, message)


def check_deps(workflow):
    from nipype.utils.filemanip import which
    return sorted(
        (node.interface.__class__.__name__, node.interface._cmd)
        for node in workflow._get_all_nodes()
        if (hasattr(node.interface, '_cmd') and
            which(node.interface._cmd.split()[0]) is None))


def get_parser():
    """Build parser object"""
    from smriprep.cli.utils import ParseTemplates, output_space as _output_space
    # from templateflow.api import templates
    from packaging.version import Version
    from ..__about__ import __version__
    # from ..config import NONSTANDARD_REFERENCES
    from .version import check_latest, is_flagged

    verstr = 'atlasTransform v{}'.format(__version__)
    currentv = Version(__version__)
    is_release = not any((currentv.is_devrelease, currentv.is_prerelease, currentv.is_postrelease))

    parser = ArgumentParser(description='atlasTransform: transforming 3D and 4D nifti files into atlas space',
                            formatter_class=ArgumentDefaultsHelpFormatter)

    # Arguments as specified by BIDS-Apps
    # required, positional arguments
    # IMPORTANT: they must go directly with the parser object
    parser.add_argument('bids_dir', action='store', type=Path,
                        help='the root folder of a BIDS valid dataset (sub-XXXXX folders should '
                             'be found at the top level in this folder).')
    parser.add_argument('output_dir', action='store', type=Path,
                        help='the output path for the outcomes of preprocessing and visual '
                             'reports')
    parser.add_argument('analysis_level', choices=['participant'],
                        help='processing stage to be run, only "participant" in the case of '
                             'atlasTransform (see BIDS-Apps specification).')
    parser.add_argument('atlas_name', choices=['craddock', 'shen'],
                        help='Which file format is the time series data coming from?')
    # optional arguments
    parser.add_argument('--resolution', choices=[1, 2],
                        help='shen atlas resolution',
                        action='store', type=int, default=1)
    parser.add_argument('--source', choices=["bold", "hurst"],
                        help='what type of file',
                        action='store', type=str, default="bold")
    parser.add_argument('--number_of_clusters', choices=CRADDOCK_CLUSTER_SIZES,
                        help='craddock atlas granularity',
                        action='store', type=int, default=200)
    parser.add_argument('--version', action='version', version=verstr)

    parser.add_argument('--algorithm', action='store', choices=['2level', 'mean', None],
                        help='which craddock algorithm to use', default='2level')

    parser.add_argument('--similarity_measure', action='store', choices=['t','s'],
                        help='which craddock similarity measure to use', default='t')

    g_bids = parser.add_argument_group('Options for filtering BIDS queries')
    g_bids.add_argument('--skip_bids_validation', '--skip-bids-validation', action='store_true',
                        default=False,
                        help='assume the input dataset is BIDS compliant and skip the validation')
    g_bids.add_argument('--participant_label', '--participant-label', action='store', nargs='+',
                        help='a space delimited list of participant identifiers or a single '
                             'identifier (the sub- prefix can be removed)')
    g_bids.add_argument('-t', '--task-id', action='store',
                        help='select a specific task to be processed')

    g_perfm = parser.add_argument_group('Options to handle performance')
    g_perfm.add_argument('--nthreads', '--n_cpus', '-n-cpus', action='store', type=int,
                         help='maximum number of threads across all processes')
    g_perfm.add_argument('--omp-nthreads', action='store', type=int, default=0,
                         help='maximum number of threads per-process')
    g_perfm.add_argument('--mem_mb', '--mem-mb', action='store', default=0, type=int,
                         help='upper bound memory limit for FMRIPREP processes')
    g_perfm.add_argument('--low-mem', action='store_true',
                         help='attempt to reduce memory usage (will increase disk usage '
                              'in working directory)')
    g_perfm.add_argument('--use-plugin', action='store', default=None,
                         help='nipype plugin configuration file')
    g_perfm.add_argument('--boilerplate', action='store_true',
                         help='generate boilerplate only')
    g_perfm.add_argument("-v", "--verbose", dest="verbose_count", action="count", default=0,
                         help="increases log verbosity for each occurence, debug level is -vvv")
    g_conf = parser.add_argument_group('Workflow configuration')

    g_other = parser.add_argument_group('Other options')
    g_other.add_argument('-w', '--work-dir', action='store', type=Path, default=Path('work'),
                         help='path where intermediate results should be stored')
    g_other.add_argument(
        '--resource-monitor', action='store_true', default=False,
        help='enable Nipype\'s resource monitoring to keep track of memory and CPU usage')
    g_other.add_argument(
        '--reports-only', action='store_true', default=False,
        help='only generate reports, don\'t run workflows. This will only rerun report '
             'aggregation, not reportlet generation for specific nodes.')
    g_other.add_argument(
        '--run-uuid', action='store', default=None,
        help='Specify UUID of previous run, to include error logs in report. '
             'No effect without --reports-only.')
    g_other.add_argument('--write-graph', action='store_true', default=True,
                         help='Write workflow graph.')
    g_other.add_argument('--stop-on-first-crash', action='store_true', default=False,
                         help='Force stopping on first crash, even if a work directory'
                              ' was specified.')
    g_other.add_argument('--notrack', action='store_true', default=True,
                         help='Opt-out of sending tracking information of this run to '
                              'the atlasTransform developers. This information helps to '
                              'improve atlasTransform and provides an indicator of real '
                              'world usage crucial for obtaining funding.')

    latest = check_latest()
    if latest is not None and currentv < latest:
        print("""\
You are using atlasTransform-%s, and a newer version of atlasTransform is available: %s.
Please check out our documentation about how and when to upgrade""" % (
            __version__, latest), file=sys.stderr)

    _blist = is_flagged()
    if _blist[0]:
        _reason = _blist[1] or 'unknown'
        print("""\
WARNING: Version %s of atlasTransform (current) has been FLAGGED
(reason: %s).
That means some severe flaw was found in it and we strongly
discourage its usage.""" % (__version__, _reason), file=sys.stderr)

    return parser


def get_workflow(logger):
    from nipype import logging as nlogging
    from multiprocessing import set_start_method, Process, Manager
    from ..utils.bids import validate_input_dir
    from .build_workflow import build_workflow
    if __name__ == 'main':
        set_start_method('forkserver')
    warnings.showwarning = _warn_redirect
    opts = get_parser().parse_args()

    exec_env = os.name

    # special variable set in the container
    # if os.getenv('IS_DOCKER_8395080871'):
    #     exec_env = 'singularity'
    #     cgroup = Path('/proc/1/cgroup')
    #     if cgroup.exists() and 'docker' in cgroup.read_text():
    #         exec_env = 'docker'
    #         if os.getenv('DOCKER_VERSION_8395080871'):
    #             exec_env = 'fmriprep-docker'

    sentry_sdk = None
    if not opts.notrack:
        import sentry_sdk
        from ..utils.sentry import sentry_setup
        sentry_setup(opts, exec_env)

    # Validate inputs
    if not opts.skip_bids_validation:
        print("Making sure the input data is BIDS compliant (warnings can be ignored in most "
              "cases).")
        validate_input_dir(exec_env, opts.bids_dir, opts.participant_label)

    # Retrieve logging level
    log_level = int(max(25 - 5 * opts.verbose_count, logging.DEBUG))
    # Set logging
    logger.setLevel(log_level)
    nlogging.getLogger('nipype.workflow').setLevel(log_level)
    nlogging.getLogger('nipype.interface').setLevel(log_level)
    nlogging.getLogger('nipype.utils').setLevel(log_level)

    # Call build_workflow(opts, retval)
    with Manager() as mgr:
        retval = mgr.dict()
        p = Process(target=build_workflow, args=(opts, retval))
        p.start()
        p.join()

        retcode = p.exitcode or retval.get('return_code', 0)

        bids_dir = Path(retval.get('bids_dir'))
        output_dir = Path(retval.get('output_dir'))
        work_dir = Path(retval.get('work_dir'))
        plugin_settings = retval.get('plugin_settings', None)
        subject_list = retval.get('subject_list', None)
        atlas_transform_wf = retval.get('workflow', None)
        run_uuid = retval.get('run_uuid', None)

    if opts.reports_only:
        sys.exit(int(retcode > 0))

    if opts.boilerplate:
        sys.exit(int(retcode > 0))

    if atlas_transform_wf and opts.write_graph:
        atlas_transform_wf.write_graph(graph2use="colored", format='svg', simple_form=True)

    retcode = retcode or int(atlas_transform_wf is None)
    if retcode != 0:
        sys.exit(retcode)

    # Check workflow for missing commands
    missing = check_deps(atlas_transform_wf)
    if missing:
        print("Cannot run atlasTransform. Missing dependencies:", file=sys.stderr)
        for iface, cmd in missing:
            print("\t{} (Interface: {})".format(cmd, iface))
        sys.exit(2)
    # Clean up master process before running workflow, which may create forks
    gc.collect()

    # Sentry tracking
    if not opts.notrack:
        from ..utils.sentry import start_ping
        start_ping(run_uuid, len(subject_list))

    return atlas_transform_wf, plugin_settings, opts, output_dir, work_dir, bids_dir, subject_list, run_uuid