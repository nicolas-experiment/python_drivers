# This Python file uses the following encoding: utf-8
# ATS9360_NPT.py driver for The aquisition board Alzar ATS9360
# Etienne Dumur <etienne.dumur@neel.cnrs.fr> 2015
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from instrument import Instrument
import numpy as np
import logging
import types
import time
import multiprocessing as mp

from ATS9360 import atsapi as ats
from ATS9360.DataAcquisition import DataAcquisition
data_acquisition = DataAcquisition()

class ATS9360_NPT(Instrument):



    def __init__(self, name):

        logging.debug(__name__ + ' : Initializing instrument')
        Instrument.__init__(self, name, tags=['measure'])

        self.add_parameter('clock_source',
            type        = types.StringType,
            flags       = Instrument.FLAG_GETSET,
            option_list = ('internal', 'external')
            )

        self.add_parameter('clock_edge',
            type        = types.StringType,
            flags       = Instrument.FLAG_GETSET,
            option_list = ('rising', 'falling')
            )

        self.add_parameter('samplerate',
            type        = types.FloatType ,
            flags       = Instrument.FLAG_GETSET,
            units       = 'MS/s'
            )

        self.add_parameter('trigger_range',
            type        = types.FloatType ,
            flags       = Instrument.FLAG_GETSET,
            option_list = (5., 2.5, 1.),
            units       = 'V'
            )

        self.add_parameter('trigger_level',
            type        = types.FloatType ,
            flags       = Instrument.FLAG_GETSET,
            units       = 'V'
            )

        self.add_parameter('trigger_delay',
            type        = types.FloatType ,
            flags       = Instrument.FLAG_GETSET,
            units       = 'ns'
            )

        self.add_parameter('trigger_slope',
            type        = types.StringType ,
            flags       = Instrument.FLAG_GETSET,
            option_list = ('positive', 'negative')
            )

        self.add_parameter('acquisition_time',
            type        = types.FloatType,
            flags       = Instrument.FLAG_GET_AFTER_SET | Instrument.FLAG_GETSET,
            units       = 'ns'
            )

        self.add_parameter('averaging',
            type        = types.IntType,
            flags       = Instrument.FLAG_GETSET
            )

        self.add_parameter('completed_acquisition',
            type        = types.FloatType,
            flags       = Instrument.FLAG_GET,
            units       = '%'
            )


        self.allow_samplerates = {1e-3   : ats.SAMPLE_RATE_1KSPS,
                                  2e-3   : ats.SAMPLE_RATE_2KSPS,
                                  5e-3   : ats.SAMPLE_RATE_5KSPS,
                                  10e-3  : ats.SAMPLE_RATE_10KSPS,
                                  20e-3  : ats.SAMPLE_RATE_20KSPS,
                                  50e-3  : ats.SAMPLE_RATE_50KSPS,
                                  100e-3 : ats.SAMPLE_RATE_100KSPS,
                                  200e-3 : ats.SAMPLE_RATE_200KSPS,
                                  500e-3 : ats.SAMPLE_RATE_500KSPS,
                                  1.     : ats.SAMPLE_RATE_1MSPS,
                                  2.     : ats.SAMPLE_RATE_2MSPS,
                                  5.     : ats.SAMPLE_RATE_5MSPS,
                                  10.    : ats.SAMPLE_RATE_10MSPS,
                                  20.    : ats.SAMPLE_RATE_20MSPS,
                                  50.    : ats.SAMPLE_RATE_50MSPS,
                                  100.   : ats.SAMPLE_RATE_100MSPS,
                                  200.   : ats.SAMPLE_RATE_200MSPS,
                                  500.   : ats.SAMPLE_RATE_500MSPS,
                                  800.   : ats.SAMPLE_RATE_800MSPS,
                                  1e3    : ats.SAMPLE_RATE_1000MSPS,
                                  1.2e3  : ats.SAMPLE_RATE_1200MSPS,
                                  1.5e3  : ats.SAMPLE_RATE_1500MSPS,
                                  1.8e3  : ats.SAMPLE_RATE_1800MSPS}


        self.allow_clock_edges = {'rising'  : ats.CLOCK_EDGE_RISING,
                                  'falling' : ats.CLOCK_EDGE_FALLING}


        self.allow_clock_sources = {'internal' : ats.INTERNAL_CLOCK,
                                    'external' : ats.EXTERNAL_CLOCK_10MHz_REF}

        # By default, we don't take into account the TTL mode for the trigger
        self.allow_trigger_ranges = {5   : ats.ETR_5V,
                                     2.5 : ats.ETR_2V5,
                                     1   : ats.ETR_1V}
                                        #    'TTL' : ats.ETR_TTL}


        self.allow_trigger_slopes = {'positive' : ats.TRIGGER_SLOPE_POSITIVE,
                                    'negative' : ats.TRIGGER_SLOPE_NEGATIVE}



        # Attributes of the clock
        self.samplerate   = 1800. # In [MS/s], float
        self.clock_source = 'external'
        self.clock_edge   = 'rising'

        # Attributes of the trigger
        self.trigger_range = 5. # In [V]
        self.trigger_slope = 'positive'
        self.trigger_level = 0.5 # In [V]
        self.trigger_delay = 0. # In [ns]

        # Attributes of the acquisition
        self.acquired_samples        = 128*80 # In S. Must be integer
        self.acquisition_time        = self.acquired_samples/1.8 # In ns, float
        self.records_per_buffer      = 100 # Must be integer
        self.nb_buffer_allocated     = 4 # Must be integer
        self.buffers_per_acquisition = 200 # Must be integer

        self._aquired_buffer = 0.

        # For the display, we get all parameters at the end of the
        # initialization
        self.get_all()



    def get_all(self):

        logging.info(__name__ + ' : get all')

        self.get_clock_edge()
        self.get_clock_source()
        self.get_samplerate()

        self.get_trigger_level()
        self.get_trigger_range()
        self.get_trigger_slope()
        self.get_trigger_delay()

        self.get_acquisition_time()
        self.get_averaging()

        self.get_completed_acquisition()



    #########################################################################
    #
    #
    #                           Methods about the parameters of the board
    #
    #
    #########################################################################


    def _get_bytes_per_buffer(self):
        """
            Return the number ob bytes per buffer of the board.
            The calculation is performed assuming that the board works in the
            NPT mode => no pre-trigger sample.
        """

        # For sake of clarity, even fixed variable are declared
        # The name of the variable is meaningfull
        bitsPerSample      = 12
        preTriggerSamples  = 0 # We assume NPT mode
        postTriggerSamples = self.acquired_samples
        channelCount       = 2 # We assume always two channels active
        recordsPerBuffer   = self.records_per_buffer

        bytesPerSample   = (bitsPerSample + 7) // 8
        samplesPerRecord = preTriggerSamples + postTriggerSamples
        bytesPerRecord   = bytesPerSample * samplesPerRecord
        bytesPerBuffer   = bytesPerRecord * recordsPerBuffer * channelCount

        return int(bytesPerBuffer)



    def _get_parameters(self):
        """
            Create a Manager for the multiprocessing containing all parameters
            needed to tune the board.
            The method returns the manager as pickable variable.
        """

        manager    = mp.Manager()
        parameters = manager.dict()

        # Clock parameters
        parameters['samplerate']   = self.samplerate
        parameters['clock_source'] = self.clock_source
        parameters['clock_edge']   = self.clock_edge

        # Trigger parameters
        parameters['trigger_range'] = self.trigger_range
        parameters['trigger_slope'] = self.trigger_slope
        parameters['trigger_level'] = self.trigger_level
        parameters['trigger_delay'] = self.trigger_delay

        # Acquisition parameters
        parameters['acquired_samples']        = self.acquired_samples
        parameters['records_per_buffer']      = self.records_per_buffer
        parameters['nb_buffer_allocated']     = self.nb_buffer_allocated
        parameters['buffers_per_acquisition'] = self.buffers_per_acquisition

        # Correspondence between user parameters and board command
        parameters['allow_samplerates']    = self.allow_samplerates
        parameters['allow_clock_edges']    = self.allow_clock_edges
        parameters['allow_clock_sources']  = self.allow_clock_sources
        parameters['allow_trigger_ranges'] = self.allow_trigger_ranges
        parameters['allow_trigger_slopes'] = self.allow_trigger_slopes

        # Communication parameters to end correctly the measurement
        parameters['measuring']        = True # True means measuring
        parameters['safe_acquisition'] = False # True means the board has been closed properly
        parameters['safe_treatment']  = [False, False] # True means the treatment is finished
        parameters['measured_buffers'] = None

        return parameters



    #########################################################################
    #
    #
    #                           Method to perform asynchroneous measurement
    #
    #
    #########################################################################


    def measurement_initialization(self, processor):
        """
            Initialize the board and launch a measurement.

            Input:
                - processor (obj instance): Instance of class coming from the
                  file DataTreatment with the class DataTreatment as parent.

            Output:
                - None
        """

        # We create shared memory to share data between processes
        queue_data_cha       = mp.Queue() # Contains measured data cha channel
        queue_data_chb       = mp.Queue() # Contains measured data chb channel

        self.queue_treatment_cha = mp.Queue() # Contains treated data
        self.queue_treatment_chb = mp.Queue() # Contains treated data

        # Obtain all the parameters to set the board
        self.parameters      = self._get_parameters()

        # We create the data treatment process
        self.worker_treat_data_cha = mp.Process(target = processor.treat_data,
                                                args   = (queue_data_cha,
                                                          self.queue_treatment_cha,
                                                          self.parameters))

        self.worker_treat_data_chb = mp.Process(target = processor.treat_data,
                                                args   = (queue_data_chb,
                                                          self.queue_treatment_chb,
                                                          self.parameters))

        # We create the data acquisition process
        self.worker_acquire_data = mp.Process(target = data_acquisition.get_data,
                                              args   = (queue_data_cha,
                                                        queue_data_chb,
                                                        self.parameters))

        # At this point the process is started
        # Consequently, the measurement is launched.
        self.worker_acquire_data.start()
        self.worker_treat_data_cha.start()
        self.worker_treat_data_chb.start()

        # The share memories are not used anymore in this process
        queue_data_cha.close()
        queue_data_chb.close()

        self._aquired_buffer = 0.


    def measurement(self):
        """
            Return the data treated with the processor given in the
            measurement_initialization method.
            Data are return everytime a buffer is empty.

            Input:
                - None
            Output:
                - None
        """

        self._aquired_buffer += 1.
        self.get_completed_acquisition()
        return self.queue_treatment_cha.get(), self.queue_treatment_chb.get()



    def measurement_close(self, transfert_info=False):
        """
            Finish properly the measurement
            First inform the board that the measurement is finished and next
            wait until the board as properly "close" the board.

            Input:
                - transfert_info (booleen): If True return the transfert rate
                information
            Output:
                - transfert_info (str): If requested the transfert info
        """

        # We inform child process that the measurement is finished
        self.parameters['measuring'] = False

        # While the child process doesn't "close" properly the board and the
        # data treatment is finished, we wait
        while not self.parameters['safe_acquisition'] and not all(self.parameters['safe_treatment']):

            pass

        # Once the board is "close" properly, we close the FIFO memory and
        # we close the child processes and the share memory
        self.queue_treatment_cha.close()
        self.queue_treatment_chb.close()
        self.worker_acquire_data.terminate()
        self.worker_treat_data_cha.terminate()
        self.worker_treat_data_chb.terminate()


        self._aquired_buffer = 0.
        self.get_completed_acquisition()

        if transfert_info:
            return self.parameters['message']



    #########################################################################
    #
    #
    #                           Acquisition
    #
    #
    #########################################################################



    def do_set_acquisition_time(self, acquisition_time):
        '''Set the acquisition time in [ns]

            Input:
                - acquisition_time (float): The acquisition time in [ns].
                 The minimum number of sample being 256.
                 The minimum acquisition time is then 256/samplerate.
                 The acquisition time will be round the closest value reachable
                 considering the samplerate.

                 The number of acquired sample must a multiple of 128.
                 The number of acquired sample will be round the closest value
                 reachable.


            Output:
                - None

                # - acquisition_time (float): The acquisition time in [ns] set
                #  in the board.
                #  - acquisition_samples (int): The number of acquired sample set
                #   in the board.
            '''

        if acquisition_time > 256./self.samplerate*1e3:

            acquired_samples      = round(self.samplerate*acquisition_time*1e-3)
            self.acquired_samples = int(round(acquired_samples/128)*128)
            self.acquisition_time = self.acquired_samples/self.samplerate*1e3

            # To display the new value of acquired sample of get it
            # self.get_acquired_samples()
        else:

            raise ValueError('The acquisition time must be longer than '\
                             +str(round(256./self.samplerate*1e3,2))+' ns.')



    def do_get_acquisition_time(self):
        '''Get the acquisition time in [ns]

            Input:
                - None.

            Output:
                - acquisition_time (float): The acquisition time in [ns].
        '''

        return self.acquisition_time



    def do_set_averaging(self, number_of_averaging):
        '''
            Set the number of averaging.
            Should be a multiple of 100

            Input:
                - number_of_averaging (int): number of averaging

            Output:
                - None.
        '''

        if int(number_of_averaging)%100:
            raise ValueError('The number of averaging should be a multiple of 100')

        self.buffers_per_acquisition = int(number_of_averaging)/self.records_per_buffer



    def do_get_averaging(self):
        '''
            Get the number of averaging

            Input:
                - None.

            Output:
                - number_of_averaging (int): number of averaging
        '''

        return self.buffers_per_acquisition*self.records_per_buffer

    #########################################################################
    #
    #
    #                           The trigger
    #
    #
    #########################################################################



    def do_set_trigger_delay(self, trigger_delay):
        '''
            Set the waitting time after which the board has received a trigger
            event before capturing a record in [ns]

            Input:
                - trigger_delay (float): Triger delay in [ns]

            Output:
                - None.
        '''

        self.trigger_delay = trigger_delay



    def do_get_trigger_delay(self):
        '''
            Get the trigger delay in [ns]

            Input:
                - None.

            Output:
                - trigger_delay (float): Triger delay in [ns]
        '''

        return self.trigger_delay



    def do_set_trigger_level(self, trigger_level):
        '''
            Set the level that the trigger source must rise above, or fall
            below, for the selected trigger to become active.

            Input:
                - trigger_level (float): Triger level in [V]
                Must be in the limit of the trigger range.

            Output:
                - None.
        '''

        # If the trigger level is in the trigger range, we accept it
        if trigger_level <  self.trigger_range and \
            trigger_level > -self.trigger_range :

            self.trigger_level = trigger_level
        else:
            raise ValueError('The trigger level must be in the input range\
                             of the trigger, here '+str(self.trigger_range)\
                             +' V.')



    def do_get_trigger_level(self):
        '''
            Get the trigger level in [V]

            Input:
                - None.

            Output:
                - trigger_level (float): Triger level in [V]
        '''

        return self.trigger_level



    def do_set_trigger_range(self, trigger_range):
        '''Set the input range of the trigger channel in [V].

            Input:
                - trigger_range (float|int): Select input range of the
                 trigger channel. Must be [5, 2.5, 1] [V].
                 The new trigger range has to contain the trigger level

            Output:
                - None.
        '''

        if trigger_range > self.trigger_level :

            self.trigger_range = trigger_range
        else:

            raise ValueError('The trigger range must contain the trigger level')



    def do_get_trigger_range(self):
        '''Get the input range of the trigger channel.

            Input:
                - None.

            Output:
                - trigger_range (float|int): Input range of the
                 trigger channel [5, 2.5, 1].
        '''

        return self.trigger_range



    def do_set_trigger_slope(self, trigger_slope):
        '''
            Set the sign of the rate of change of the trigger signal
            with time when it crosses the trigger voltage level that is
            required to generate a trigger event.

            Input:
                - trigger_range (string): ['positive', 'negative'].

            Output:
                - None.
        '''
        self.trigger_slope = trigger_slope.lower()



    def do_get_trigger_slope(self):
        '''
            Get the sign of the rate of change of the trigger signal
            with time when it crosses the trigger voltage level that is
            required to generate a trigger event.

            Input:
                - None.

            Output:
                - trigger_range (string): ['positive', 'negative'].
        '''

        return self.trigger_slope



    #########################################################################
    #
    #
    #                           The clock
    #
    #
    #########################################################################



    def do_set_clock_edge(self, clock_edge):
        '''Set the clock edge of the board.

            Input:
                - clock_edge (string): Select the external clock edge on which
                                       to latch samples data. Must be either
                                       "rising" or "failing".

            Output:
                - None.
        '''

        if clock_edge.lower() in self.allow_clock_edges:

            self.clock_edge = clock_edge.lower()
        else:
            raise ValueError('Samplerate not allowed by the board')



    def do_get_clock_edge(self):
        '''Get the clock edge of the board.

            Input:
                - None.

            Output:
                - clock_edge (string): The external clock edge on which
                                       to latch samples data. Either
                                       "rising" or "failing".
        '''

        return self.clock_edge



    def do_set_samplerate(self, samplerate):
        '''Set the samplerate of the board.

            Input:
                - samplerate (float): If the clock source is internal
                  the samplerate must be one of the following string: 1e-3,
                  2e-3, 5e-3, 10e-3, 20e-3, 50e-3, 100e-3, 200e-3, 500e-3, 1.,
                  2., 5., 10., 20., 50., 100., 200., 500., 800., 1e3, 1.2e3,
                  1.5e3, 1.8e3.

                  If the clock is set to be external (assumed 10MHz external
                  clock), all samplerates greater than 300MHz and smaller than
                  1800MHZ being a multiple of 1 MHz are allowed [should be
                  given in MS/s].

            Output:
                - None.
        '''

        # If the board uses its internal clock, only certains samplerate are
        # allowed, see dictionnary self.samplerates.

        # If the board uses its external clock, all samplerates greater than
        # 300MHz and smaller than 1800MHZ being a multiple of 1 MHz are
        # allowed.

        if self.clock_source == 'internal':

            if samplerate in self.allow_samplerates:

                self.samplerate = float(samplerate)

                # To display the new value of acquisition time
                self.set_acquisition_time(self.acquired_samples/self.samplerate*1e3)
            else:

                raise ValueError('Samplerate not allowed by the board')

        elif self.clock_source == 'external':

            if samplerate >= 300. and samplerate <= 1800.:

                self.samplerate = float(samplerate)

                # To display the new value of acquisition time
                self.set_acquisition_time(self.acquired_samples/self.samplerate*1e3)
            else:

                raise ValueError('Samplerate not allowed by the board')
        else:

            raise ValueError('The clock source must be set to "internal"\
                              or "external".')



    def do_get_samplerate(self):
        '''Get the samplerate of the board.

            Input:
                -

            Output:
                -
        '''

        return self.samplerate



    def do_set_clock_source(self, clock_source):
        '''Set the clock source of the board.

            Input:
                - clock_source (string): Must be either "internal" or
                 "external".

            Output:
                - None.
        '''

        if clock_source.lower() in self.allow_clock_sources:

            self.clock_source = clock_source.lower()
        else:

            raise ValueError('clock_source argument must be "internal" or \
                             "external"')



    def do_get_clock_source(self):
        '''Get the clock source of the board.

            Input:
                -

            Output:
                -
        '''

        return self.clock_source



    #########################################################################
    #
    #
    #                           The clock
    #
    #
    #########################################################################



    def do_get_completed_acquisition(self):
        """
            Return the percentage of completed acquisition.

            Input:
                - None

            Output:
                - percentage (float)
        """


        return round(self._aquired_buffer*100./self.buffers_per_acquisition, 2)
