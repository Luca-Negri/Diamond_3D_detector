#
# Copyright (C) 2018 Pico Technology Ltd. See LICENSE file for terms.
#
# PS2000A BLOCK MODE EXAMPLE
# This example opens a 2000a driver device, sets up two channels and a trigger then collects a block of data.
# This data is then plotted as mV against time in ns.


import ctypes
import numpy as np
from picosdk.ps2000a import ps2000a as ps
import matplotlib.pyplot as plt
from picosdk.functions import adc2mV, assert_pico_ok,mV2adc


class WaveformReader:

  def __init__(self,Volt_rangeA=3,Volt_rangeB=2,Trigger_value=-12,Trigger_type=2):
    
    '''Classe per interfacciarsi con la scheda di acquisizione
      picoscope2206b.

      Contiene: init(Volt_range=3,Trigger_value=2048)
                run()
                run2()



      init: Inizializza l'oscilloscopio e i parametri di misura del 
            canaleA
 
            Volt_range=seleziona tra 10 diversi range di voltaggio
                      1= 20 mV PP 
                      2= 50 mV PP
                      3= 100 mV PP
                      4= 200 mV PP
                      5= 500 mV PP
                      6= 1 V PP
                      7= 2 V PP
                      8= 5 V PP
                      9= 10 V PP
                      10= 20 V PP

            Trigger_value= valore in ordine di cicli dell'ADC per 
                        far scattare il Trigger

            Trigger_type= tipo di trigger, da selezionare tra 
                      1= ABOVE 
                      1= BELOW 
                      1= RISING 
                      1= FALLING
                      1= RISING_OR_FALLING

    run2: aziona una singola presa dati dell'oscilloscopio, in
          memoria i dati sono registrati sugli array di classe t,C1,C2

    '''




    # Create chandle and status ready for use
    self.chandle = ctypes.c_int16()
    self.status = {}

    # Open 2000 series PicoScope
    # Returns handle to chandle for use in future API functions
    self.status["openunit"] = ps.ps2000aOpenUnit(ctypes.byref(self.chandle), None)
    assert_pico_ok(self.status["openunit"])


    maxADC = ctypes.c_int16()
    self.status["maximumValue"] = ps.ps2000aMaximumValue(self.chandle, ctypes.byref(maxADC))
    assert_pico_ok(self.status["maximumValue"])

    self.Voltrange=Volt_rangeA
    self.VoltrangeB=Volt_rangeB
    self.trigger_value=mV2adc(Trigger_value, self.VoltrangeB, maxADC)
    self.Trigger_type=Trigger_type


    # Set up channel A
    # handle = chandle
    # channel = PS2000A_CHANNEL_A = 0
    # enabled = 1
    # coupling type = PS2000A_DC = 1
    # range = PS2000A_2V = 7
    # analogue offset = 0 V
    self.chARange = self.Voltrange
    self.status["setChA"] = ps.ps2000aSetChannel(self.chandle, 0, 1, 1, self.chARange, 0)
    assert_pico_ok(self.status["setChA"])

    # Set up channel B
    # handle = chandle
    # channel = PS2000A_CHANNEL_B = 1
    # enabled = 1
    # coupling type = PS2000A_DC = 1
    # range = PS2000A_2V = 7
    # analogue offset = 0 V
    self.chBRange = self.VoltrangeB
    self.status["setChB"] = ps.ps2000aSetChannel(self.chandle, 1, 1, 1, self.chBRange, 0)
    assert_pico_ok(self.status["setChB"])

    # Set up single trigger
    # handle = chandle
    # enabled = 1
    # source = PS2000A_CHANNEL_A = 0
    # threshold = 1024 ADC counts
    # direction = PS2000A_RISING = 2
    # delay = 0 s
    # auto Trigger = 1000 ms
    self.status["trigger"] = ps.ps2000aSetSimpleTrigger(self.chandle, 1, 1, self.trigger_value, self.Trigger_type, 0, 0)

    assert_pico_ok(self.status["trigger"])

    # Set number of pre and post trigger samples to be collected
    self.preTriggerSamples = 2500
    self.postTriggerSamples = 4500
    self.totalSamples = self.preTriggerSamples + self.postTriggerSamples

    # Get timebase information
    # handle = chandle
    # timebase = 8 = timebase
    # noSamples = totalSamples
    # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalNs)
    # pointer to totalSamples = ctypes.byref(returnedMaxSamples)
    # segment index = 0
    self.timebase = 1
    self.timeIntervalns = ctypes.c_float()
    self.returnedMaxSamples = ctypes.c_int32()
    self.oversample = ctypes.c_int16(0)
    self.status["getTimebase2"] = ps.ps2000aGetTimebase2(self.chandle,
                                                  self.timebase,
                                                  self.totalSamples,
                                                  ctypes.byref(self.timeIntervalns),
                                                  self.oversample,
                                                  ctypes.byref(self.returnedMaxSamples),
                                                  0)
    assert_pico_ok(self.status["getTimebase2"])
  def run(self):
    # Run block capture
    # handle = chandle
    # number of pre-trigger samples = preTriggerSamples
    # number of post-trigger samples = PostTriggerSamples
    # timebase = 8 = 80 ns = timebase (see Programmer's guide for mre information on timebases)
    # oversample = 0 = oversample
    # time indisposed ms = None (not needed in the example)
    # segment index = 0
    # lpReady = None (using ps2000aIsReady rather than ps2000aBlockReady)
    # pParameter = None
    self.status["runBlock"] = ps.ps2000aRunBlock(self.chandle,
                                          self.preTriggerSamples,
                                          self.postTriggerSamples,
                                          self.timebase,
                                          self.oversample,
                                          None,
                                          0,
                                          None,
                                          None)
    
    assert_pico_ok(self.status["runBlock"])

    # Check for data collection to finish using ps2000aIsReady
    ready = ctypes.c_int16(0)
    check = ctypes.c_int16(0)
    while ready.value == check.value:
      self.status["isReady"] = ps.ps2000aIsReady(self.chandle, ctypes.byref(ready))

    # Create buffers ready for assigning pointers for data collection
    bufferAMax = (ctypes.c_int16 * self.totalSamples)()
    bufferAMin = (ctypes.c_int16 * self.totalSamples)() # used for downsampling which isn't in the scope of this example
    bufferBMax = (ctypes.c_int16 * self.totalSamples)()
    bufferBMin = (ctypes.c_int16 * self.totalSamples)() # used for downsampling which isn't in the scope of this example

    # Set data buffer location for data collection from channel A
    # handle = chandle
    # source = PS2000A_CHANNEL_A = 0
    # pointer to buffer max = ctypes.byref(bufferDPort0Max)
    # pointer to buffer min = ctypes.byref(bufferDPort0Min)
    # buffer length = totalSamples
    # segment index = 0
    # ratio mode = PS2000A_RATIO_MODE_NONE = 0
    self.status["setDataBuffersA"] = ps.ps2000aSetDataBuffers(self.chandle,
                                                       0,
                                                       ctypes.byref(bufferAMax),
                                                       ctypes.byref(bufferAMin),
                                                       self.totalSamples,
                                                       0,
                                                       0)
    assert_pico_ok(self.status["setDataBuffersA"])

    # Set data buffer location for data collection from channel B
    # handle = chandle
    # source = PS2000A_CHANNEL_B = 1
    # pointer to buffer max = ctypes.byref(bufferBMax)
    # pointer to buffer min = ctypes.byref(bufferBMin)
    # buffer length = totalSamples
    # segment index = 0
    # ratio mode = PS2000A_RATIO_MODE_NONE = 0
    self.status["setDataBuffersB"] = ps.ps2000aSetDataBuffers(self.chandle,
                                                       1,
                                                       ctypes.byref(bufferBMax),
                                                       ctypes.byref(bufferBMin),
                                                       self.totalSamples,
                                                       0,
                                                       0)
    assert_pico_ok(self.status["setDataBuffersB"])

    # Create overflow location
    overflow = ctypes.c_int16()
    # create converted type totalSamples
    cTotalSamples = ctypes.c_int32(self.totalSamples)

    # Retried data from scope to buffers assigned above
    # handle = chandle
    # start index = 0
    # pointer to number of samples = ctypes.byref(cTotalSamples)
    # downsample ratio = 0
    # downsample ratio mode = PS2000A_RATIO_MODE_NONE
    # pointer to overflow = ctypes.byref(overflow))
    self.status["getValues"] = ps.ps2000aGetValues(self.chandle, 0, ctypes.byref(cTotalSamples), 0, 0, 0, ctypes.byref(overflow))
    assert_pico_ok(self.status["getValues"])


    # find maximum ADC count value
    # handle = chandle
    # pointer to value = ctypes.byref(maxADC)
    maxADC = ctypes.c_int16()
    self.status["maximumValue"] = ps.ps2000aMaximumValue(self.chandle, ctypes.byref(maxADC))
    assert_pico_ok(self.status["maximumValue"])

    # convert ADC counts data to mV
    self.waveformA =  adc2mV(bufferAMax, self.chARange, maxADC)
    self.waveformB =  adc2mV(bufferBMax, self.chBRange, maxADC)

    # Create time data
    self.t = np.linspace(0, (cTotalSamples.value) * self.timeIntervalns.value, cTotalSamples.value)

    # plot data from channel A and B
    #plt.plot(self.t, self.waveformA[:])
    # plt.plot(time, adc2mVChBMax[:])
    #plt.xlabel('Time (ns)')
    #plt.ylabel('Voltage (mV)')
    #plt.show()


    # Stop the scope
    # handle = chandle
    #self.status["stop"] = ps.ps2000aStop(self.chandle)
    #assert_pico_ok(self.status["stop"])

    # Close unitDisconnect the scope
    # handle = chandle
    #self.status["close"] = ps.ps2000aCloseUnit(self.chandle)
    #assert_pico_ok(self.status["close"])

    # display status returns
    #print(self.status)
    return self.t,self.waveformA,self.waveformB    


if __name__=='__main__':

  acq=WaveformReader()
  while True:
    acq.run()


    plt.plot(acq.t, acq.waveformB[:])
     #plt.plot(time, adc2mVChBMax[:])
    plt.xlabel('Time (ns)')
    plt.ylabel('Voltage (mV)')
    plt.show()
  



