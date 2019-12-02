import re, os
from math import sqrt, pi, log, exp

methods = {'Line', 'Point', 'RC'}

class LfpElectrode:

    def __init__(self,
                 x, y, z,
                 sampling_period=0.1,  # in ms
                 method='Line',  # see LFPsimpy.methods
                 exclude_regex=".*(?:dummy|myelin|node|branch).*"):

        if method not in methods:
            raise KeyError('Method must be one of: ' + str(methods))

        self.method = method
        self.sampling_period = sampling_period

        self.elec_x = x
        self.elec_y = y
        self.elec_z = z

        self.exclude_regex = re.compile(exclude_regex)

        self.section_lfps = {}

        self.values = []
        self.times = []

        from neuron import h
        self.h = h

        self.insert()

        self.setup_recorder()

        self.nrn_value_tracker = None

        self.setup_neuron_plot_vars()

        self.check_parallel()

    def check_parallel(self):
        h = self.h
        self.parallel_ctx = ctx = h.ParallelContext()
        self.is_parallel = ctx.nhost() > 1

    def setup_neuron_plot_vars(self):
        h = self.h

        # Load the dummy class
        dir = os.path.abspath(os.path.dirname(__file__))
        h.load_file(os.path.join(dir, 'LFPsimpy.hoc'))

        # Initialize it - value is updated in compute()
        self.nrn_value_tracker = h.LfpElectrode()

    def is_lfp_section(self, sec_name):
        return self.exclude_regex.match(sec_name) is None

    def insert(self):
        h = self.h

        if not hasattr(h, 'cvode'):
            h.load_file('stdrun.hoc')

        if not h.cvode.use_fast_imem():
            h.cvode.use_fast_imem(1)
            h.init()

        if self.method == 'Point':
            LfpClass = SectionLfpPointMethod

        elif self.method == 'Line':
            LfpClass = SectionLfpLineMethod

        else: # self.method == 'RC':
            LfpClass = SectionLfpRCMethod

        for sec in h.allsec():
            if self.is_lfp_section(sec.name()):

                # Let NEURON create 3D points if missing
                if h.n3d(sec=sec) <= 0:
                    h.define_shape(sec=sec)

                # Keep track of sections being monitored
                self.section_lfps[sec] = LfpClass(self, sec)

    def compute(self):
        # The first value from i_membrane_ is almost always invalid
        # e.g. extremelly large
        if self.h.t == 0:
            return 0

        # Sum the LFPs of each section
        result = sum(sec_lfp.compute() for sec_lfp in self.section_lfps.values())

        # If in parallel also sum across all ranks
        if self.is_parallel:
            all_results = self.parallel_ctx.py_gather(result, 0)

            # Sum only on the root rank
            if all_results is not None:
                result = sum(all_results)

        # Update the dummy class on the root rank only
        if self.parallel_ctx.id() == 0:

            # Update the dummy class
            self.nrn_value_tracker.value = result

        return result

    def collect(self):
        h = self.h

        if h.t > h.tstop:
            if h.t - h.tstop > h.dt and not self.is_parallel or self.parallel_ctx.id() == 0:
                print('Note: h.t (%s) is more than h.tstop (%s). Please ensure h.tstop is set before '
                      'h.run() or pc.psolve(). Stopping LFP collection. If h.t and h.tstop are within rounding error, '
                      'you can safely ignore this message.' % (h.t, h.tstop))

            return

        # There is a bug where under MPI, due to differences in rounding errors on different ranks,
        # the last NetStim event does not always get delivered on all ranks causing an MPI timeout during py_gather.
        # This workaround avoids collecting on the very last step. But it requires that h.tstop
        # be set each time simulation is advanced.
        if h.t > h.tstop - self.sampling_period:
            return

        time = self.h.t
        value = self.compute()

        self.times.append(time)
        self.values.append(value)

    def clear(self):
        self.values = []
        self.times = []

    def setup_recorder(self):
        h = self.h

        collector_stim = h.NetStim(0.5)
        collector_stim.start = 0
        collector_stim.interval = self.sampling_period
        collector_stim.number = 1e9
        collector_stim.noise = 0

        collector_con = h.NetCon(collector_stim, None)
        collector_con.record(self.collect)

        self.collector_stim = collector_stim
        self.collector_con = collector_con

        # Clear previously recorded activity on h.run()
        self.fih = h.FInitializeHandler(self.clear)


class SectionLfp:
    sigma = 0.3
    radius_margin = 0.1

    # set to specific capacitance, Johnston and Wu 1995
    capa = 1

    # velo um/ms  #  Nauhaus et al, 2009 calculated the propagation speed on average
    # 0.24 +/- 0.20 m/s in monkeys and
    # 0.31 +/- 0.23 m/s in cats (mean +/- s.d.)
    # ie, 240 um/ms
    velo = 240

    def __init__(self, electrode, sec):
        self.electrode = electrode
        self.sec = sec
        self.radius = sec.diam / 2.0

        self.transfer_resistance = self.compute_transfer_resistance()

    def compute_transfer_resistance(self):
        raise NotImplementedError()

    def compute(self):
        tr = self.transfer_resistance

        return sum(tr * seg.i_membrane_ for seg in self.sec)

    def dist_to_electrode(self):
        # Prep variables
        h = self.electrode.h

        x3d = h.x3d
        y3d = h.y3d
        z3d = h.z3d

        elec_x = self.electrode.elec_x
        elec_y = self.electrode.elec_y
        elec_z = self.electrode.elec_z

        sec = self.sec

        diam = sec.diam
        radius = diam / 2.0

        # Start computing
        x = (x3d(0, sec=sec) + x3d(1, sec=sec)) / 2
        y = (y3d(0, sec=sec) + y3d(1, sec=sec)) / 2
        z = (z3d(0, sec=sec) + z3d(1, sec=sec)) / 2

        dis = sqrt(
            ((elec_x - x) * (elec_x - x)) +
            ((elec_y - y) * (elec_y - y)) +
            ((elec_z - z) * (elec_z - z))
        )

        # setting radius limit
        if dis < radius:
            dis = radius + self.radius_margin

        return dis


class SectionLfpPointMethod(SectionLfp):
    def compute_transfer_resistance(self):
        electrode_dist = self.dist_to_electrode()

        transfer_resitance = 1 / (4 * pi * electrode_dist * self.sigma)

        # So the calculated signal will be in nV
        transfer_resitance *= 1e-1

        # To make usable with cvode.use_fast_imem
        transfer_resitance *= 100

        return transfer_resitance


class SectionLfpLineMethod(SectionLfp):
    def compute_transfer_resistance(self):
        # Prep variables
        h = self.electrode.h

        area = h.area

        x3d = h.x3d
        y3d = h.y3d
        z3d = h.z3d

        elec_x = self.electrode.elec_x
        elec_y = self.electrode.elec_y
        elec_z = self.electrode.elec_z

        sec = self.sec

        radius = self.radius

        # calculate length of the compartment
        dist_comp_x = x3d(1, sec=sec) - x3d(0, sec=sec)
        dist_comp_y = y3d(1, sec=sec) - y3d(0, sec=sec)
        dist_comp_z = z3d(1, sec=sec) - z3d(0, sec=sec)

        sum_dist_comp = sqrt(
            (dist_comp_x * dist_comp_x) +
            (dist_comp_y * dist_comp_y) +
            (dist_comp_z * dist_comp_z)
        )

        if sum_dist_comp < radius:
            sum_dist_comp = radius + self.radius_margin

        long_dist_x = (elec_x - x3d(1, sec=sec))
        long_dist_y = (elec_y - y3d(1, sec=sec))
        long_dist_z = (elec_z - z3d(1, sec=sec))

        sum_HH = (long_dist_x * dist_comp_x) + \
                 (long_dist_y * dist_comp_y) + \
                 (long_dist_z * dist_comp_z)

        final_sum_HH = sum_HH / sum_dist_comp

        sum_temp1 = (long_dist_x * long_dist_x) + \
                    (long_dist_y * long_dist_y) + \
                    (long_dist_z * long_dist_z)

        r_sq = sum_temp1 - (final_sum_HH * final_sum_HH)

        Length_vector = final_sum_HH + sum_dist_comp

        if final_sum_HH < 0 and Length_vector <= 0:
            top = sqrt((final_sum_HH * final_sum_HH) + r_sq) - final_sum_HH
            bottom = sqrt((Length_vector * Length_vector) + r_sq) - Length_vector
            phi = top / bottom

        elif final_sum_HH > 0 and Length_vector > 0:
            top = sqrt((Length_vector * Length_vector) + r_sq) + Length_vector
            bottom = sqrt((final_sum_HH * final_sum_HH) + r_sq) + final_sum_HH
            phi = top / bottom

        else:
            A = sqrt((Length_vector * Length_vector) + r_sq) + Length_vector
            B = sqrt((final_sum_HH * final_sum_HH) + r_sq) - final_sum_HH
            phi = (A * B) / r_sq

        phi = log(phi)

        transfer_resistance = 1 / (4 * pi * sum_dist_comp * self.sigma) * phi

        # So the calculated signal will be in nV
        transfer_resistance *= 1e-1

        # To make usable with cvode.use_fast_imem
        transfer_resistance *= 100

        return transfer_resistance


class SectionLfpRCMethod(SectionLfp):
    def compute_transfer_resistance(self):
        # Prep variables
        area = self.electrode.h.area

        # Start computing
        dis = self.dist_to_electrode()

        RC = self.sigma * self.capa

        time_const = dis / self.velo
        transfer_resistance = exp(-time_const / RC)

        # So the calculated signal will be in nV
        transfer_resistance *= 1e-3

        # To make usable with cvode.use_fast_imem
        transfer_resistance *= 100

        return transfer_resistance
