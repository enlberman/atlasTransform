# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
fractal scaling calculation workflow
=====
"""

import logging
from multiprocessing import set_start_method

logging.addLevelName(25, 'IMPORTANT')  # Add a new level between INFO and WARNING
logging.addLevelName(15, 'VERBOSE')  # Add a new level between INFO and DEBUG
logger = logging.getLogger('cli')


def main():
    """Entry point"""
    from .run_utils import get_workflow
    if __name__ == 'main':
        set_start_method('forkserver')
    errno = 1  # Default is error exit unless otherwise set
    workflow, plugin_settings, opts, output_dir, work_dir, bids_dir, subject_list, run_uuid = get_workflow(logger)

    try:
        workflow.run(**plugin_settings)
    except Exception as e:
        if not opts.notrack:
            pass
        logger.critical('atlasTransform failed: %s', e)
        raise
    else:
        errno = 0
        logger.log(25, 'atlasTransform finished without errors')
        if not opts.notrack:
            pass#sentry_sdk.capture_message('atlasTransform finished without errors',
                   #                    level='info')
    # finally:
    #     from niworkflows.reports import generate_reports
    #     from subprocess import check_call, CalledProcessError, TimeoutExpired
    #     from pkg_resources import resource_filename as pkgrf
    #     from shutil import copyfile
    #
    #     citation_files = {
    #         ext: output_dir / 'atlasTransform' / 'logs' / ('CITATION.%s' % ext)
    #         for ext in ('bib', 'tex', 'md', 'html')
    #     }
    #
    #     if citation_files['md'].exists():
    #         # Generate HTML file resolving citations
    #         cmd = ['pandoc', '-s', '--bibliography',
    #                pkgrf('atlasTransform', 'data/boilerplate.bib'),
    #                '--filter', 'pandoc-citeproc',
    #                '--metadata', 'pagetitle="atlasTransform citation boilerplate"',
    #                str(citation_files['md']),
    #                '-o', str(citation_files['html'])]
    #
    #         logger.info('Generating an HTML version of the citation boilerplate...')
    #         try:
    #             check_call(cmd, timeout=10)
    #         except (FileNotFoundError, CalledProcessError, TimeoutExpired):
    #             logger.warning('Could not generate CITATION.html file:\n%s',
    #                            ' '.join(cmd))
    #
    #         # Generate LaTex file resolving citations
    #         cmd = ['pandoc', '-s', '--bibliography',
    #                pkgrf('atlasTransform', 'data/boilerplate.bib'),
    #                '--natbib', str(citation_files['md']),
    #                '-o', str(citation_files['tex'])]
    #         logger.info('Generating a LaTeX version of the citation boilerplate...')
    #         try:
    #             check_call(cmd, timeout=10)
    #         except (FileNotFoundError, CalledProcessError, TimeoutExpired):
    #             logger.warning('Could not generate CITATION.tex file:\n%s',
    #                            ' '.join(cmd))
    #         else:
    #             copyfile(pkgrf('atlasTransform', 'data/boilerplate.bib'),
    #                      citation_files['bib'])
    #     else:
    #         logger.warning('atlasTransform could not find the markdown version of '
    #                        'the citation boilerplate (%s). HTML and LaTeX versions'
    #                        ' of it will not be available', citation_files['md'])
    #
    #     # Generate reports phase
    #     failed_reports = generate_reports(
    #         subject_list, output_dir, work_dir, run_uuid, packagename='atlasTransform')
    #     write_derivative_description(bids_dir, output_dir / 'atlasTransform')
    #
    #     if failed_reports and not opts.notrack:
    #         sentry_sdk.capture_message(
    #             'Report generation failed for %d subjects' % failed_reports,
    #             level='error')
    #     sys.exit(int((errno + failed_reports) > 0))


if __name__ == '__main__':
    raise RuntimeError("atlasTransform/cli/run.py should not be run directly;\n"
                       "Please `pip install` atlasTransform and use the `atlasTransform` command")
