import sys
import os
import argparse
from shutil import copyfile
from collections import OrderedDict
import numpy as np

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from model import manager, creator
from Utilities import tfs_pandas, logging_tools
from tfs_files import TfsCollection, Tfs

LOGGER = logging_tools.get_logger(__name__)

X, Y = "x", "y"
PLANES = (X, Y)


def _parse_args():
    '''
    Parses the arguments, checks for valid input and returns tuple
    It needs also the input needed to define the accelerator:
    --accel=<accel_name>
    and all the rest of the parameters needed to define given accelerator.
    e.g. for LHC runII 2017 beam 1
    --accel lhc --lhcmode lhc_runII_2017 --beam 1
    '''
    accel_cls, rest_args = manager.get_accel_class_from_args(
        sys.argv[1:]
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement",
                        help=("Path to measurement files, "
                              "usually the GetLLM output dir."),
                        dest="measurement", required=True)
    parser.add_argument("--model",
                        help=("Model from where to get the segments and "
                              "elements definitions, all BPMs and elements "
                              "defined in --elements and --segments have to "
                              "be present in this model."),
                        dest="model", required=True)
    parser.add_argument("--optics",
                        help=("Path to the optics file to use, usually "
                              "the path to the modifiers.madx file."),
                        dest="optics", required=True)
    parser.add_argument("--elements",
                        help=("Comma separated element name list "
                              "to run in element mode."),
                        dest="elements")
    parser.add_argument("--segments",
                        help=("Segments to run in segment mode with format: "
                              "segment_name1,start1,end1;segment_name2,start2,end2;"
                              "where start and end must be existing BPM names."),
                        dest="segments")
    parser.add_argument("--output",
                        help=("Directory where to put the output files."),
                        dest="output", required=True)
    options = parser.parse_args(rest_args)
    return accel_cls, options


def segment_by_segment(accel_cls, options):
    """
    TODO
    """
    segments = _parse_segments(options.segments)
    elements = _parse_elements(options.elements)
    if not segments and not elements:
        raise SbsDefinitionError("No segments or elements provided in the input.")
    if _there_are_duplicated_names(segments, elements):
        raise SbsDefinitionError("Duplicated names in segments and elements.")
    model = tfs_pandas.read_tfs(options.model)
    meas = GetLlmMeasurement(options.measurement)
    elem_segments = [Segment.init_from_element(name) for name in elements]
    for segment in elem_segments + segments:
        seg_beatings = run_for_segment(accel_cls, segment, model, meas,
                                       options.optics, options.output)
        write_beatings(seg_beatings)


def run_for_segment(accel_cls, segment, model, meas, optics, output):
    """
    TODO
    """
    bpm_eval_funct = _bpm_is_in_beta_meas
    new_segment = improve_segment(segment, model, meas, bpm_eval_funct)
    LOGGER.info("Evaluating segment {} ({}, {}). Was input as {} ({}, {})."
                .format(new_segment.name, new_segment.start, new_segment.end,
                        segment.name, segment.start, segment.end))
    _prepare_for_madx(new_segment, meas, optics, output)
    segment_mdl = accel_cls.get_segment(
        new_segment.name, new_segment.start, new_segment.end,
        optics,
    )
    _run_madx(segment, segment_mdl, output)
    seg_models = SegmentModels(output, segment)
    return compute_beatings(seg_models, meas)


def improve_segment(segment, model, meas, eval_funct):
    """Returns a new segment with elements that satisfies eval_funct.

    This function takes a segment with start and end that might not
    satisfy 'eval_funct' and searchs the next element that satisfies
    it, returning a new segment with the new start and end elements.

    Arguments:
        segment: The segment to be processed.
        model: The model where to take all the element names from. Both the
            start and end of the segment have to be present in this model
            NAME attribute.
        meas: An instance of the Measurement class that will be passed to
            'eval_funct' to check elements for validity.
        eval_funct: An user-porvided function that takes an element name as
            first argument and an instance of the Measurement class as second,
            and returns True only if the element is evaluated as good start or
            end for the segment, usually checking for presence in the
            measurement and not too large error.
    Returns:
        A new segment with generally different start and end but always the
        same name and element attributes.
    """
    names = list(model.NAME)
    for name in (segment.start, segment.end):
        if name not in names:
            raise SbsDefinitionError(
                "Element name {} not in the input model.".format(name)
            )

    def eval_funct_meas(name):
        return eval_funct(name, meas)

    new_start = _select_closest(segment.start, names, eval_funct_meas, back=True)
    new_end = _select_closest(segment.end, names, eval_funct_meas, back=False)
    new_segment = Segment(segment.name, new_start, new_end)
    new_segment.element = segment.element
    return new_segment


def compute_beatings(seg_models, meas):
    """
    TODO
    """
    # TODO: beta-beating
    # TODO: phase-beating
    # TODO: coupling
    # TODO: dispersion
    # TODO: chromatic?
    # TODO: special elements?
    pass


def write_beatings(seg_beatings):
    """
    TODO
    """
    pass


def _parse_segments(segments_str):
    segments = []
    names = []
    clean_segm_str = segments_str.strip()
    if clean_segm_str == "":
        raise SbsDefinitionError("Empty segment definition string.")
    for single_definition in clean_segm_str.split(";"):
        if single_definition.strip() == "":
            continue
        name_start_end = single_definition.split(",")
        try:
            name, start, end = name_start_end
        except ValueError:
            raise SbsDefinitionError(
                "Unable to parse segment string {}.".format(name_start_end)
            )
        else:
            name, start, end = name.strip(), start.strip(), end.strip()
            if name in names:
                raise SbsDefinitionError(
                    "Duplicated segment name {}".format(name)
                )
            segments.append(Segment(name, start, end))
            names.append(name)
    return segments


def _parse_elements(elements_str):
    clean_elems_str = elements_str.strip()
    if clean_elems_str == "":
        raise SbsDefinitionError("Empty element definition string.")
    if clean_elems_str.endswith(","):
        clean_elems_str = clean_elems_str[:-1]
    elements = [element_name.strip()
                for element_name in clean_elems_str.split(",")]
    if len(set(elements)) != len(elements):
        raise SbsDefinitionError("Duplicated names in element list.")
    return elements


def _there_are_duplicated_names(segments, elements):
    seg_names = [segment.name for segment in segments]
    return not set(seg_names).isdisjoint(elements)


def _select_closest(name, all_names, eval_cond, back=False):
    new_name = name
    while not eval_cond(new_name):
        delta = 1 if not back else -1
        next_index = (all_names.index(new_name) + delta) % len(all_names)
        new_name = all_names[next_index]
        if name == new_name:
            raise SbsDefinitionError(
                "No elements remaining after filtering. "
                "Probably wrong model or bad measurement."
            )
    return new_name


def _bpm_is_in_beta_meas(bpm_name, meas):
    # 'elem in pandasSeries' doesnt seem to work...
    return (bpm_name in list(meas.beta[X].NAME) and
            bpm_name in list(meas.beta[Y].NAME))


def _prepare_for_madx(segment, meas, optics, output):
    copyfile(optics, os.path.join(output, "modifiers.madx"))
    meas_file_content = _prepare_meas_file(segment, meas)
    meas_file_path = os.path.join(
        output,
        "measurement_{}.madx".format(segment.name)
    )
    with open(meas_file_path, "w") as meas_file:
        meas_file.write(meas_file_content)
    corr_file_path = os.path.join(
        output,
        "corrections_{}.madx".format(segment.name)
    )
    # TODO do this properly:
    open(corr_file_path, "w").close()


def _prepare_meas_file(segment, meas):
    # TODO: Better solution for all this, extremelly ugly
    meas_dict = OrderedDict()

    for plane in PLANES:
        for suffix, name in (("_ini", segment.start), ("_end", segment.end)):
            meas_dict["bet{}{}".format(plane, suffix)] =\
                getattr(meas.beta[plane], "BET{}".format(plane.upper()))[name]
            meas_dict["alf{}{}".format(plane, suffix)] =\
                getattr(meas.beta[plane], "ALF{}".format(plane.upper()))[name]
        meas_dict["alf{}_end".format(plane)] = -meas_dict["alf{}_end".format(plane)]

    try:
        for plane in PLANES:
            for suffix, name in (("_ini", segment.start), ("_end", segment.end)):
                meas_dict["d{}{}".format(plane, suffix)] =\
                    getattr(meas.disp[plane], "D{}".format(plane.upper()))[name]
                meas_dict["dp{}{}".format(plane, suffix)] =\
                    getattr(meas.disp[plane], "DP{}".format(plane.upper()))[name]
        meas_dict["dp{}_end".format(plane)] = -meas_dict["dp{}_end".format(plane)]
    except IOError:
        LOGGER.debug("No dispersion files in the input directory.")
    except KeyError:
        LOGGER.debug("Start or end BPMs not in dispersion files.")

    # TODO: W function and phi

    try:
        for prefix, name in (("ini_", segment.start), ("end_", segment.end)):
            (meas_dict["{}r11".format(prefix)],
             meas_dict["{}r12".format(prefix)],
             meas_dict["{}r21".format(prefix)],
             meas_dict["{}r22".format(prefix)]) = _get_r_terms(name, meas)
    except IOError:
        LOGGER.debug("No coupling files in the input directory.")
    except KeyError:
        LOGGER.debug("Start or end BPMs not in coupling files.")

    meas_file_content = ""
    for key in meas_dict:
        meas_file_content += "{} = {};\n".format(key, meas_dict[key])
    return meas_file_content


def _get_r_terms(name, meas):
    betx = meas.beta[X].BETX[name]
    bety = meas.beta[Y].BETY[name]
    alfx = meas.beta[X].ALFX[name]
    alfy = meas.beta[Y].ALFY[name]
    f1001r = meas.coupling.F1001R[name]
    f1001i = meas.coupling.F1001I[name]
    f1010r = meas.coupling.F1010R[name]
    f1010i = meas.coupling.F1010I[name]
    if (f1001r, f1001i, f1010r, f1010i) == (0., 0., 0., 0.):
        return 0., 0., 0., 0.,

    ga11 = 1 / np.sqrt(betx)
    ga12 = 0
    ga21 = alfx / np.sqrt(betx)
    ga22 = np.sqrt(betx)
    Ga = np.reshape(np.array([ga11, ga12, ga21, ga22]), (2, 2))

    gb11 = 1 / np.sqrt(bety)
    gb12 = 0
    gb21 = alfy / np.sqrt(bety)
    gb22 = np.sqrt(bety)
    Gb = np.reshape(np.array([gb11, gb12, gb21, gb22]), (2, 2))

    J = np.reshape(np.array([0, 1, -1, 0]), (2, 2))

    absf1001 = np.sqrt(f1001r ** 2 + f1001i ** 2)
    absf1010 = np.sqrt(f1010r ** 2 + f1010i ** 2)

    gamma2 = 1. / (1. + 4. * (absf1001 ** 2 - absf1010 ** 2))
    c11 = (f1001i + f1010i)
    c22 = (f1001i - f1010i)
    c12 = -(f1010r - f1001r)
    c21 = -(f1010r + f1001r)
    Cbar = np.reshape(2 * np.sqrt(gamma2) *
                         np.array([c11, c12, c21, c22]), (2, 2))

    C = np.dot(np.linalg.inv(Ga), np.dot(Cbar, Gb))
    jCj = np.dot(J, np.dot(C, -J))
    c = np.linalg.det(C)
    r = -c / (c - 1)
    R = np.transpose(np.sqrt(1 + r) * jCj)
    r11, r12, r21, r22 = np.ravel(R)
    return r11, r12, r21, r22


def _run_madx(segment, segment_mdl, output):
    mad_file_name = 't_' + str(segment.name) + '.madx'
    log_file_name = segment.name + "_mad.log"
    madx_file_path = os.path.join(output, mad_file_name)
    log_file_path = os.path.join(output, log_file_name)
    creator.create_model(segment_mdl, "segment", output,
                         logfile=log_file_path, writeto=madx_file_path)
    LOGGER.info("MAD-X done, log file: {}".format(log_file_path))


class Segment(object):
    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end
        self.element = None

    @staticmethod
    def init_from_element(element_name):
        fake_segment = Segment(element_name, element_name, element_name)
        fake_segment.element = element_name
        return fake_segment


class GetLlmMeasurement(TfsCollection):
    """Class to hold and load the measurements from GetLLM.

    The class will try to load the _free file, then the _free2 and then the
    normal file, if none of them if present an IOError will be raised.

    Arguments:
        directory: The path to the measurement directory, usually a GetLLM
            output directory.
    """
    beta = Tfs("getbeta")
    amp_beta = Tfs("getampbeta")
    kmod_beta = Tfs("getkmodbeta")
    phase = Tfs("getphase")
    phasetot = Tfs("getphasetot")
    disp = Tfs("getD")
    coupling = Tfs("getcouple", two_planes=False)
    norm_disp = Tfs("getNDx", two_planes=False)

    def get_filename(self, prefix, plane=None):
        if plane is None:
            plane = ""
        templ = prefix + "{}{}.out"
        for filename in (templ.format(plane, "_free"),
                         templ.format(plane, "_free2"),
                         templ.format(plane, "")):
            if os.path.isfile(os.path.join(self.directory, filename)):
                return filename
        raise IOError("No file name found for prefix {} in {}."
                      .format(prefix, self.directory))


class SegmentModels(TfsCollection):
    """
    Class to hold and load the models of the segments created by MAD-X.

    Arguments:
        directory: The path where to find the models.
        segment: A segment instance corresponding to the model to load.
    """

    front = Tfs("twiss_{}.dat", two_planes=False)
    back = Tfs("twiss_{}_back.dat", two_planes=False)
    front_corrected = Tfs("twiss_{}_cor.dat", two_planes=False)
    back_corrected = Tfs("twiss_{}_cor_back.dat", two_planes=False)

    def __init__(self, directory, segment):
        super(SegmentModels, self).__init__(directory)
        self.segment = segment

    def get_filename(self, template):
        return template.format(self.segment.name)


class SegmentBeatings(TfsCollection):
    """
    TODO
    """

    beta_phase = Tfs("sbsbetabeating{plane}_{name}.dat")
    beta_kmod = Tfs("sbskmodbetabeating{plane}_{name}.dat")
    beta_amp = Tfs("sbsampbetabeating{plane}_{name}.dat")
    phase = Tfs("sbsphase{plane}t_{name}.dat")
    coupling = Tfs("sbscouple_{name}.dat", two_planes=False)
    disp = Tfs("sbsD{plane}_{name}.dat")
    norm_disp = Tfs("sbsNDx_{name}.dat", two_planes=False)

    def __init__(self, directory, seg_name):
        super(SegmentBeatings, self).__init__(directory)
        self.seg_name = seg_name

    def get_filename(self, template, plane=None):
        if plane is None:
            return template.format(name=self.seg_name)
        return template.format(plane=plane, name=self.seg_name)


class SbsDefinitionError(Exception):
    """
    TODO
    """
    pass


def _i_am_main():
    _accel_cls, _options = _parse_args()
    segment_by_segment(_accel_cls, _options)


if __name__ == "__main__":
    _i_am_main()
