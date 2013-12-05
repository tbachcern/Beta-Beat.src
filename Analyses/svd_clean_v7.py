#---------------------------------
# Reads SDDS ASCII files
# Removes bad BPM (flat signal, SVD mode over threshold)
# Also removes the noise floor of the data to enhance physical signal
# Ram Calaga, Dec 30, 2003
# @ Glenn => made it possible to filter on space
#
# version 2 20120-09-05 (tbach):
# - major refactoring (introduced real class objects, removed all globals,
#  removed a lot of not necessary switches and conversions, and more)
# - order of bad BPMs can be different to previous versions
# - formatting of bad BPMs is different to previous versions (The column
#  order is the same as a normal SDDS ASCII file now, added a reason why
#  the BPM is bad)
# - output formating is different to previous versions (only for whitespaces to
#  make it human readable)
# - Improved speed a lot (biggest change was from O(n*n*n) to O(n*n)). Previous
#  runs had around 20 seconds, now 3 seconds)
# - Data output is in all test cases the same, but can be different if
#  different bad BPM contribute to the same mode in the SVD
#
# version 3 2012-09-13 (tbach):
# - writing for bad BPM changed
# - flat BPM detection made before matrix creation
#
# version 4 2012-09-21 (tbach):
# - only one svd call for every plane needed now
#  (reduces previous 4 calls to now 2 calls)
# - the rearrangeent of the SVD calculation changes some part of the data.
#  Previous: Matrix M, do SVD from M, find bad BPMs from SVD,
#   remove this bad BPMs from M, redo SVD from M, cut singular values,
#   create M from cutted SVD
#  Now:      Matrix M, do SVD from M, find bad BPMs from SVD,
#   remove this bad BPMs from SVD results,        cut singular values,
#   create M from cutted SVD
#  From tests, the data was different, but only with a small derivation
#  which looked ok
#
# version 5 2012-10-15 (tbach):
# - fixed the startturn and maxturn argument handling, did not work in
#  previous versions
# - beautified the print output
# - introduced newfile argument. This can be used to specify a new filename if
#  overriding is not wanted
#
# version 6 2012-11-21 (tbach)
# - updated variable and function names and formatting according to
#  python style guide
#
# version 7 2013-03-19 (tbach)
# - header for bad bpm file now according to sdds ascii v1 specification
# - shortened bad bpm handling a bit (from vmaier)
#
# usage: python svd_clean -f filename
# -> outputs filename (overrides)

"""
This file cleans BPM turn by turn data.
The input is expected in the SDDS ASCII Format.
Criteria to remove bad bpm:
-flat, this mean the difference between min and max value
 for all turns is smaller than a given threshold
-SVD dominant: A singular value decomposition is applied to the bpms x turns
 matrix. If there is dominant mode above a threshold, this will be removed

After this, the singular values are used to filter the noise.
All singular value below a given threshold are zeroed.

In the end, the new file is written again.
"""

import sys
import os
import time

from numpy import dot as matrixmultiply

import optparse
import numpy

# option parser
parser = optparse.OptionParser(usage="python %prog -f file [other options]",
    version="%prog 6")
parser.add_option("-t", "--turn",
    help="Turn number to start. Default is first turn: 1",
    default="1", dest="startturn", type="int")
parser.add_option("-m", "--maxturns",
    help="Maximum number of turns to be analysed. Default is a number that is "
     +"lower than the maximum which can be handled by drive: 9.500",
    default="9500", dest="maxturns", type="int")

parser.add_option("-v", "--sing_val",
    help="Keep this amount of singular values in decreasing order, rest will "
     +"be cut (set to 0). Default is a large number: 1e5",
    default="100000", dest="sing", type="int")

parser.add_option("-p", "--pk-2-pk",
    help="Peak to peak amplitude cut. This removes BPMs where "
    +"abs(max(turn values) - min(turn values)) <= threshold. Default is 10e-8",
    default="0.00000001", dest="peak", type="float")
parser.add_option("-s", "--sumsquare",
    help="Threshold for single BPM dominating a mode. Should be > 0.9 for LHC."
    + " Default is 0.925",
    default="0.925", dest="sum", type="float")

parser.add_option("-f", "--file",
    help="File to clean",
    default="./", dest="file")
parser.add_option("-n", "--newfile",
    help="File name for new file. Default is override current file",
    default="", dest="newfile")

parser.add_option("--use_test_mode",
    help="Set testing mode, this prevents date writing and file overwriting",
    action="store_true", dest="use_test_mode")


(options, args) = parser.parse_args()

# Input variables check
if len(options.file) <= 2:
    print "Exit: Missing file name, use --help to see usage"
    sys.exit(1)

# INPUT VARIABLES
startturn_human = options.startturn # turn to start, human readable
                                    # (startindex 1, not 0)
startturn = startturn_human - 1     # turn to start
pk_pk_cut = options.peak            # peak to peak amplitude
sumsquare = options.sum             # sqroot(sumsquare of the 4 bpm values)
                                    #  should be > 0.9
sing_val = options.sing             # keep svdcut number of singular values
                                    #  in decreasing order
maxturns_human = options.maxturns   # maximum number of turns to parse, 
                                    # human readable (startindex 1, not 0)
maxturns = maxturns_human - 1       # maximum number of turns to parse
newfile = options.newfile           # new file for SVDClean output
if newfile == "":                   # set default input
    newfile = options.file
    print "no newfile given, existing file will be replaced with output"
use_test_mode = options.use_test_mode

# internal options
print_times = False  # If True, (more) execution times will be printed
print_debug = False  # If True, internal debug information will be printed

# internal constants
plane_x = "0"
plane_y = "1"


class SddsFile(object):
    """This class represents a SDDS file.
    It reads an existing SDDS file and creates & writes the new one"""
    def __init__(self, path_to_sddsfile):
        self.path_to_sddsfile = path_to_sddsfile
        self.bad_bpmfile = BadBpmFile(path_to_sddsfile)
        self.parsed = False
        self.header = ""
        self.number_of_turns = 0
        self.dictionary_plane_to_bpms = { plane_x:Bpms(), plane_y:Bpms() }

    def init(self):
        """Parse the current SDDS file and sets all member variables"""
        if (self.parsed):
            return
        time_start = time.time()

        last_number_of_turns = 0
        detected_number_of_turns = 0
        flatbpm_counter = 0

        filesdds = open(self.path_to_sddsfile, "r")
        print "Extracting data from file..."
        for line in filesdds:  # Iterator over all lines (tbach)
            if line.startswith("#"):  # we have a comment line (tbach)
                self.header += line
                continue

            # from here, we have a data line (tbach)
            list_splitted_line_values = line.split()
            number_of_columns = len(list_splitted_line_values)
            if (number_of_columns < 3):  # this is not a valid data line (tbach)
                continue
            plane = list_splitted_line_values[0]
            bpm_name = list_splitted_line_values[1]
            location = float(list_splitted_line_values[2])

            # first 3 entries metadata, rest should be turn data (tbach)
            detected_number_of_turns = number_of_columns - 3

            if last_number_of_turns > 0:
                if last_number_of_turns != detected_number_of_turns:
                    print "(plane", plane, ") BPM has a different number of turns then previous. BPM:", bpm_name, "previous turns:", last_number_of_turns, "current turns:", detected_number_of_turns
                    sys.exit(1)
            # the else part will happen only once, if last_number_of_turns <= 0
            # (or multiple times if we do not have any turn data) (tbach)
            else:
                if (startturn_human > detected_number_of_turns):
                    print "startturn > detected_number_of_turns. startturn:", startturn_human, "detected_number_of_turns:", detected_number_of_turns
                    sys.exit(1)
            last_number_of_turns = detected_number_of_turns

            bpms_name_location_plane = (bpm_name, location, plane)
            # be careful with the bpms_name_location_plane format,
            # it is important for other parts of the program
            # -- tbach

            self.number_of_turns = min(maxturns, detected_number_of_turns) - startturn
            ndarray_line_data = numpy.array(list_splitted_line_values[3 + startturn:3 + startturn + self.number_of_turns], dtype=numpy.float64)
            # this block handles BPMs with the same values for all turns (tbach)
            peak_to_peak_difference = numpy.abs(numpy.max(ndarray_line_data) - numpy.min(ndarray_line_data))
            if peak_to_peak_difference <= pk_pk_cut:  # then do not use this BPM (tbach)
                reason_for_badbpm = "Flat BPM, the difference between all values is smaller than " + str(pk_pk_cut)
                badbpm = BadBpm(bpms_name_location_plane, ndarray_line_data, reason_for_badbpm)
                self.bad_bpmfile.add_badbpm(badbpm)
                flatbpm_counter += 1
                continue

            self.dictionary_plane_to_bpms[plane].bpm_data.append(ndarray_line_data)
            self.dictionary_plane_to_bpms[plane].bpms_name_location_plane.append(bpms_name_location_plane)

        filesdds.close()
        self.parsed = True
        if print_times:
            print ">>Time for init (read file):", time.time() - time_start, "s"
        if flatbpm_counter > 0:
            print "Flat BPMs detected. Number of BPMs removed:", flatbpm_counter
        print "Startturn:", startturn_human, "Maxturns:", maxturns_human
        print "Number of turns:", self.number_of_turns
        print "Horizontal BPMs:", self.dictionary_plane_to_bpms[plane_x].get_number_of_bpms(),
        print "Vertical BPMs:", self.dictionary_plane_to_bpms[plane_y].get_number_of_bpms()
        print "Reading done"

    def remove_bpms(self, badbpm_indices, plane, reason):
        """Removes the given BPMs for the given plane with the given reason"""
        badbpms = self.dictionary_plane_to_bpms[plane].remove_badbpm_and_get_badbpms(badbpm_indices, reason)
        self.bad_bpmfile.add_badbpms(badbpms)

    def write_file(self):
        """Writes the new file"""
        self.bad_bpmfile.header = self.header
        self.bad_bpmfile.write_badbpms()
        print "writing data to temp file: " + self.path_to_sddsfile + ".tmp_svd_clean"
        time_start = time.time()
        fileclean = open(self.path_to_sddsfile + ".tmp_svd_clean", "w")
        fileclean.write(self.header)
        if "NTURNS calculated" not in self.header:
            fileclean.write("#NTURNS calculated: " + str(self.number_of_turns) + "\n")
        #fileclean.write("#Modified: {0} By: {1}\n".format(time.strftime("%Y-%m-%d#%H:%M:%S"), __file__)) # to get only the filename: os.path.basename(__file__)
        # The previous line requires at least python 2.6 (tbach)
        if not use_test_mode:
            fileclean.write("#Modified: %s By: %s\n" % (time.strftime("%Y-%m-%d#%H:%M:%S"), __file__)) # to get only the filename: os.path.basename(__file__)
        self.write_bpm_data_to_file(plane_x, fileclean)
        self.write_bpm_data_to_file(plane_y, fileclean)
        fileclean.close()
        if print_times:
            print ">>Time for write_file:", time.time() - time_start, "s"

        print "writing done. rename to:  ", newfile
        if not use_test_mode:
            os.remove(newfile)
            os.rename(options.file + ".tmp_svd_clean", newfile)

    def write_bpm_data_to_file(self, plane, file_to_write):
        """Writes the BPM data for the given plane"""
        current_bpms = self.dictionary_plane_to_bpms[plane]
        for i, bpms_name_location_plane_item in enumerate(current_bpms.bpms_name_location_plane):
            # file_to_write.write("{0} {1[0]:<15} {1[1]:>12.5f} ".format(plane, bpms_name_location_plane_item)) # This line requires at least python 2.6 (tbach)
            # {0} is the first argument, {1[0]} from the second argument the first entry, {1[1] from the second argument the second entry (tbach)
            # :>15 means right aligned, filled up to 15 characters. example: "   BPMYA.4L1.B1" (tbach)
            # :>12.5 means right aligned float, filled up to 12 characters and fixed precision of 5. Example: " 23347.14262" (tbach)
            file_to_write.write("%s %15s %12.5f " % (plane, bpms_name_location_plane_item[0], bpms_name_location_plane_item[1]))
            current_bpms.bpm_data[i].tofile(file_to_write, sep=" ", format="% 8.5f")
            # % 8.5f is a float, filled up to 8 characters and fixed precision of 5. if negative, preceded by a sign, if positive by a space (tbach)
            # Example1: " -0.94424", example2: "  1.25630" (tbach)
            file_to_write.write("\n")


class BadBpmFile(object):
    """ Represents a bad bpm file
    Handles interaction with the bad bpm file
    """
    
    def __init__(self, path_to_sddsfile):
        self.path_to_sddsfile = path_to_sddsfile
        self.path_to_badbpmfile = path_to_sddsfile.replace(".new", "") + ".bad"
        self.header = ""
        self.lines_to_write = []

    def __write_header(self, filehandle_badbpm):
        """ Writes the header for the bad bpm file """
        filehandle_badbpm.write(self.header)
        if not use_test_mode:
            filehandle_badbpm.write("#Modified: %s By: %s\n" % (time.strftime("%Y-%m-%d#%H:%M:%S"), __file__)) # to get only the filename: os.path.basename(__file__)
        filehandle_badbpm.write("#Bad BPMs from: %s \n" % self.path_to_sddsfile)

    def add_badbpm(self, badbpm):
        """ Adds a new bad BPM to write """
        self.lines_to_write.append("%s %15s %12.5f %s \n#%s\n" % \
                                 (badbpm.plane, badbpm.name, badbpm.location, " ".join(["%12.5f" % x for x in badbpm.data]), badbpm.reason))
        # for string formatting explanation, see write_bpm_data_to_file (tbach)
        # requires at least python 2.6:
        # "{0} {1:<15} {2:>12.5f} {3} \n# {4}\n".format(badbpm.plane, badbpm.name, badbpm.location, " ".join(["{0:>10.5f}".format(x) for x in badbpm.data])
        # --tbach

    def add_badbpms(self, list_badbpm):
        """ Adds all bad BPM to write """
        for badbpm in list_badbpm:
            self.add_badbpm(badbpm)

    def write_badbpms(self):
        """ Writes all the current bad BPM"""
        if not self.lines_to_write:
            return
        time_start = time.time()
        print "Create file for bad BPMs: ", self.path_to_badbpmfile
        file_badbpms = open(self.path_to_badbpmfile, "w")
        self.__write_header(file_badbpms)
        for line in self.lines_to_write:
            file_badbpms.write(line)
        file_badbpms.close()
        if print_times:
            print ">>Time for write_badbpms:", time.time() - time_start, "s"


class Bpms(object):
    """This represents some BPMs.
    It is used to distinguish between BPMs for X and Y"""
    
    def __init__(self):
        self.bpm_data = []
        self.bpms_name_location_plane = []

    def get_number_of_bpms(self):
        """ Get the number of BPMs"""
        return len(self.bpms_name_location_plane)

    def remove_badbpm_and_get_badbpms(self, badbpm_indices, reason):
        """ Removes the given BPM indices from the current BPM list
        and returns a list of the given bad BPMs"""
        badbpms = []
        for index in sorted(badbpm_indices, reverse=True):
            badbpms.append(BadBpm(self.bpms_name_location_plane.pop(index), self.bpm_data.pop(index), reason))

        return badbpms


class BadBpm(object):
    """Represents a bad BPM"""
    
    def __init__(self, bpms_name_location_plane, data, reason):
        self.bpms_name_location_plane = bpms_name_location_plane
        self.data = data
        self.reason = reason  # The reason why this is a bad bpm (tbach)

    @property
    def name(self):
        """ returns the name from bpms_name_location_plane"""
        return self.bpms_name_location_plane[0]

    @property
    def location(self):
        """ returns the location from bpms_name_location_plane"""
        return self.bpms_name_location_plane[1]

    @property
    def plane(self):
        """ returns the plane from bpms_name_location_plane"""
        return self.bpms_name_location_plane[2]


class SvdHandler(object):
    """ Main workload class. Handles the SVD"""
    
    def __init__(self):
        self.sddsfile = SddsFile(options.file)
        self.sddsfile.init()
        print ""

        time_start = time.time()
        self.do_svd_clean(plane_x)
        self.do_svd_clean(plane_y)
        if print_times:
            print ">>Time for svdClean (all):", time.time() - time_start, "s"
        print ""

        self.sddsfile.write_file()
        print ""

    def do_svd_clean(self, plane):
        """Does a SVD clean on the given plane"""
        time_start = time.time()
        print "(plane", plane, ") removing noise floor with SVD"

        A = numpy.array(self.sddsfile.dictionary_plane_to_bpms[plane].bpm_data)
        number_of_bpms = A.shape[0]

        if number_of_bpms <= 10:
            sys.exit("Number of bpms <= 10")

        # normalise the matrix
        sqrt_number_of_turns = numpy.sqrt(A.shape[1])
        A_mean = numpy.mean(A)
        A = (A - A_mean) / sqrt_number_of_turns

        if print_times:
            print ">>Time for svdClean (before SVD call):", time.time() - time_start, "s"
        USV = self.get_singular_value_decomposition(A)
        if print_times:
            print ">>Time for svdClean (after SVD call): ", time.time() - time_start, "s"

        # remove bad BPM by SVD (tbach)
        goodbpm_indices = self.get_badbpm_indices(USV, plane)
        USV = (USV[0][goodbpm_indices], USV[1], USV[2])
        number_of_bpms = len(goodbpm_indices)

        #----SVD cut for noise floor
        if sing_val < number_of_bpms:
            print "(plane", plane, ") svdcut:", sing_val
            USV[1][sing_val:] = 0
        else:
            print "requested more singular values than available"

        A = matrixmultiply(USV[0], matrixmultiply(numpy.diag(USV[1]), USV[2]))
        # A0 * (A1 * A2) should require less operations than (A0 * A1) * A2,
        #  because of the different sizes
        # A0 has (M, K), A1 has (K, K) and A2 has (K, N) with K=min(M,N)
        # Most of the time, the number of turns is greater then
        #  the number of BPM, so M > N
        # --tbach
        A = (A * sqrt_number_of_turns) + A_mean
        self.sddsfile.dictionary_plane_to_bpms[plane].bpm_data = A
        if print_times:
            print ">>Time for do_svd_clean:", time.time() - time_start, "s"

    def get_singular_value_decomposition(self, matrix):
        """Calls the SVD, returns a USV representation
        For details, see numpy documentation"""
        return numpy.linalg.svd(matrix, full_matrices=False)  # full matrices do not have any interesting value for us (tbach)

    def get_badbpm_indices(self, USV, plane):
        """ Get the indices from bad BPMs for the given plane"""
        time_start = time.time()

        # A is [u,s,v] with u * np.diag(s) * v = original matrix (tbach)
        U_t_abs = numpy.transpose(abs(USV[0]))  # This creates a view, which is nice and fast (tbach)
        # What happens here?
        # From the SDDS ASCII file, We have a BPM x Turns matrix.
        # Let B = Number of BPM, T = Number of Turns, then matrix size is (B,T)
        # If we do the SVD, we have U,S,V. U has the size (B,x) and V (x,T)
        # If we transpose, U^t has the size (x,B)
        # Now, we can look in every row to get the maximum value for every BPM.
        # If one BPM is dominating, we remove it as a bad BPM
        # --tbach

        badbpm_indices = set()  # we do not want duplicates (tbach)

        for row_index in range(len(U_t_abs)):
            max_index = numpy.argmax(U_t_abs[row_index])
            max_value = U_t_abs[row_index][max_index]
            if (max_value > sumsquare):
                badbpm_indices.add(max_index)

        if print_debug:
            print "Bad BPM indices: ", badbpm_indices

        number_of_badbpms = len(badbpm_indices)
        if number_of_badbpms > 0:
            print "(plane", plane, ") Bad BPMs from SVD detected. Number of BPMs removed:", len(badbpm_indices)

        # add the bad BPMs to the general list of bad BPMs (tbach)
        reason_for_badbpm = "Detected from SVD, single peak value is greater then " + str(sumsquare)
        self.sddsfile.remove_bpms(badbpm_indices, plane, reason_for_badbpm)

        number_of_bpms = USV[0].shape[0]
        goodbpm_indices = range(number_of_bpms)
        for value in badbpm_indices:
            goodbpm_indices.remove(value)

        if print_times:
            print ">>Time for removeBadBpms:", time.time() - time_start, "s"
        return goodbpm_indices


TIME_START_GLOBAL = time.time()
SvdHandler()
print "Global Time:", time.time() - TIME_START_GLOBAL, "s"