"""
This Python script produces the responses of the beta, phase and horizontal dispersion
on the magnet strength provided by a json file.
The response matrix is stored in a 'pickled' file.

These response matrices are used to calculate the corrections by the correction scripts.
"""

import os
import math
import cPickle
import argparse
import multiprocessing
import json
import numpy
import pandas

from Utilities import tfs_pandas
from madx import madx_wrapper
from Utilities import logging_tools
from Utilities.contexts import timeit
from Utilities.iotools import create_dirs

EXCLUDE_CATEGORIES_DEFAULT = ["LQ", "MQX", "MQXT", "Q", "QIP15", "QIP2", "getListsByIR"]

LOG = logging_tools.get_logger(__name__)

"""
================================= Parse Arguments ===========================================
"""


def _parse_args(args=None):
    """ Parses the arguments, checks for valid input and returns options """
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--outfile",
                        help="Name of fullresponse file.",
                        dest="outfile_path",
                        required=True,
                        type=str)
    parser.add_argument("-t", "--tempdir",
                        help=("Directory to store the temporary MAD-X files, "
                              "it will default to the directory containing 'outfile'."),
                        dest="temp_dir",
                        default=None,
                        type=str)
    parser.add_argument("-v", "--variables",
                        help="Path to file containing variable lists",
                        dest="varfile_path",
                        required=True,
                        type=str)
    parser.add_argument("-j", "--jobfile",
                        help="Name of the original MAD-X job file defining the sequence file.",
                        dest="original_jobfile_path",
                        required=True,
                        type=str)
    parser.add_argument("-p", "--pattern",
                        help=("Pattern to be replaced in the MAD-X job file "
                              "by the iterative script calls."),
                        default="%CALL_ITER_FILE%",
                        dest="pattern",
                        type=str)
    parser.add_argument("-k", "--deltak",
                        help="delta K1L to be applied to quads for sensitivity matrix",
                        default=0.00002,
                        dest="delta_k",
                        type=float)
    parser.add_argument("-n", "--num_proc",
                        help="Number of processes to use in parallel.",
                        default=multiprocessing.cpu_count(),
                        dest="num_proc",
                        type=int)
    parser.add_argument("-e", "--exclude",
                        help="Categories to be excluded in variables json-file",
                        default=EXCLUDE_CATEGORIES_DEFAULT,
                        dest="exclude_categories",
                        type=str,
                        nargs='+')

    options = parser.parse_args(args)

    if not options.temp_dir:
        options.temp_dir = os.path.dirname(options.outfile)
    create_dirs(options.temp_dir)

    return options


"""
================================= FullResponse ===========================================
"""


def _generate_fullresponse(options):
    """ Generate a dictionary containing response matrices for
        Mu, BetaBeating, Dispersion and Tune and saves it to a file.
    """
    LOG.debug("Generating Fullresponse.")
    with timeit(lambda t: LOG.debug("  Total time generating fullresponse: {:f}s".format(t))):
        variables = _get_variables_from_file(options.varfile_path, options.exclude_categories)

        process_pool = multiprocessing.Pool(processes=options.num_proc)

        incr_dict = _generate_madx_jobs(variables, options)
        _call_madx(process_pool, options.temp_dir, options.num_proc)
        _clean_up(options.temp_dir, options.num_proc, options.outfile_path)

        var_to_twiss = _load_madx_results(variables, process_pool, incr_dict, options.temp_dir)
        fullresponse = _create_fullresponse_from_dict(var_to_twiss)
    _save_fullresponse(options.outfile_path, fullresponse)


def _get_variables_from_file(varfile_path, exclude_categories):
    """ Load variables list from json file """
    LOG.debug("Loading variables from file {:s}".format(varfile_path))

    with open(varfile_path, 'r') as varfile:
        var_dict = json.load(varfile)

    variables = []
    for category in var_dict.keys():
        if category not in exclude_categories:
            variables += var_dict[category]
    return list(set(variables))


def _generate_madx_jobs(variables, options):
    """ Generates madx job-files """
    LOG.debug("Generating MADX jobfiles.")
    incr_dict = {'0': 0.0}
    vars_per_proc = int(math.ceil(float(len(variables)) / options.num_proc))

    for proc_idx in range(options.num_proc):
        jobfile_path, iterfile_path = _get_jobfiles(options.temp_dir, proc_idx)
        _write_jobfile(options.original_jobfile_path, jobfile_path, iterfile_path, options.pattern)
        with open(iterfile_path, "w") as iter_file:
            for i in range(vars_per_proc):
                var_idx = proc_idx * vars_per_proc + i
                if var_idx >= len(variables):
                    break
                var = variables[var_idx]
                incr_dict[var] = options.delta_k
                iter_file.write(
                    "{var:s}={var:s}+({delta:f});\n".format(var=var, delta=options.delta_k))
                iter_file.write(
                    "twiss, file='{:s}';\n".format(os.path.join(options.temp_dir, "twiss." + var)))
                iter_file.write(
                    "{var:s}={var:s}-({delta:f});\n".format(var=var, delta=options.delta_k))

            if proc_idx == options.num_proc - 1:
                iter_file.write(
                    "twiss, file='{:s}';\n".format(os.path.join(options.temp_dir, "twiss.0")))

    return incr_dict


def _write_jobfile(original_jobfile_path, jobfile_path, iterfile_path, pattern):
    """ Replaces the pattern in the original jobfile with call to the appropriate iterfile
        and saves as new numbered jobfile
    """
    with open(original_jobfile_path, "r") as original_file:
        original_str = original_file.read()
    with open(jobfile_path, "w") as job_file:
        job_file.write(original_str.replace(
            pattern, "call, file='{:s}';".format(iterfile_path),
        ))


def _call_madx(process_pool, temp_dir, num_proc):
    """ Call madx in parallel """
    LOG.debug("Starting {:d} MAD-X jobs...".format(num_proc))
    madx_jobs = [_get_jobfiles(temp_dir, index)[0] for index in range(num_proc)]
    process_pool.map(_launch_single_job, madx_jobs)
    LOG.debug("MAD-X jobs done.")


def _clean_up(temp_dir, num_proc, outfile):
    """ Merge Logfiles and clean temporary outputfiles """
    LOG.debug("Cleaning output and building log...")
    full_log = ""
    for index in range(num_proc):
        job_path, iter_path = _get_jobfiles(temp_dir, index)
        log_path = job_path + ".log"
        with open(log_path, "r") as log_file:
            full_log += log_file.read()
        os.remove(log_path)
        os.remove(job_path)
        os.remove(iter_path)
    with open(outfile + ".log", "w") as full_log_file:
        full_log_file.write(full_log)


def _load_madx_results(variables, process_pool, incr_dict, temp_dir):
    """ Load the madx results in parallel and return var-tfs dictionary """
    LOG.debug("Loading Madx Results.")
    vars_and_paths = []
    for value in variables + ['0']:
        vars_and_paths.append((value, temp_dir))
    var_to_twiss = {}
    for var, tfs_data in process_pool.map(_load_and_remove_twiss, vars_and_paths):
        tfs_data['incr'] = incr_dict[var]
        var_to_twiss[var] = tfs_data
    return var_to_twiss


def _create_fullresponse_from_dict(var_to_twiss):
    """ Convert var-tfs dictionary to fullresponse dictionary """
    resp = pandas.Panel.from_dict(var_to_twiss)
    resp = resp.transpose(2, 0, 1)
    # After transpose e.g: resp[NDX, kqt3, bpm12l1.b1]
    # The magnet called "0" is no change (nominal model)
    resp['NDX'] = resp.xs('DX', axis=0) / numpy.sqrt(resp.xs('BETX', axis=0))
    resp['NDY'] = resp.xs('DY', axis=0) / numpy.sqrt(resp.xs('BETY', axis=0))
    resp['BBX'] = resp.xs('BETX', axis=0) / resp.loc['BETX', '0', :]
    resp['BBY'] = resp.xs('BETY', axis=0) / resp.loc['BETY', '0', :]
    resp = resp.subtract(resp.xs('0'), axis=1)
    # Remove beta-beating of nominal model with itself (bunch of zeros)
    resp.drop('0', axis=1, inplace=True)
    resp = resp.div(resp.loc['incr', :, :])
    return {'MUX': resp.xs('MUX', axis=0),
            'MUY': resp.xs('MUY', axis=0),
            'BBX': resp.xs('BBX', axis=0),
            'BBY': resp.xs('BBY', axis=0),
            'NDX': resp.xs('NDX', axis=0),
            'NDY': resp.xs('NDY', axis=0),
            'Q': resp.loc[['Q1', 'Q2'], :, resp.minor_axis[0]]
            }


def _save_fullresponse(outputfile_path, fullresponse):
    """ Dumping the FullResponse file """
    LOG.debug("Saving Fullresponse into file '{:s}'".format(outputfile_path))
    with open(outputfile_path, 'wb') as dump_file:
        cPickle.Pickler(dump_file, -1).dump(fullresponse)


def _get_jobfiles(temp_dir, index):
    """ Return names for jobfile and iterfile according to index """
    jobfile_path = os.path.join(temp_dir, "job.iterate.{:d}.madx".format(index))
    iterfile_path = os.path.join(temp_dir, "iter.{:d}.madx".format(index))
    return jobfile_path, iterfile_path


def _launch_single_job(inputfile_path):
    """ Function for pool to start a single madx job """
    log_file = inputfile_path + ".log"
    return madx_wrapper.resolve_and_run_file(inputfile_path, log_file=log_file)


def _load_and_remove_twiss(var_and_path):
    """ Function for pool to retrieve results """
    (var, path) = var_and_path
    twissfile = os.path.join(path, "twiss." + var)
    tfs_data = tfs_pandas.read_tfs(twissfile)
    tfs_data = tfs_data.set_index('NAME')
    tfs_data['Q1'] = tfs_data.Q1
    tfs_data['Q2'] = tfs_data.Q2
    os.remove(twissfile)
    return var, tfs_data


if __name__ == '__main__':
    with timeit(lambda t:
                LOG.debug("  Generated FullResponse in {:f}s".format(t))):
        _generate_fullresponse(_parse_args())
