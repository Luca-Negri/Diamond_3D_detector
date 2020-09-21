import numpy as np 
import pandas as pd 
import time 
from tqdm import tqdm 
from glob import glob 
import re 
import matplotlib.pyplot as plt
class FakeWaveformReader:
    def __init__ (self, folder = None, checklength = False ):
      ''' Legge i file delle prese dati e li trasferisce quando si chiama la funzione read
      
          Se si desidera controllare che tutti i file abbiano la stessa lunghezza, impostare checklenght=True '''
      self._folder = folder or "/home/lucio/timespotwp2_cce_measurement/LucaData/Agosto31/C?Trace*.txt"
      self._files = glob(self._folder)
        
      nfiles=len(self._files)

      self._waveformIds = []
      for fname in self._files:
        waveformId = re.findall (r".*C[0-9]Trace([0-9]*)\.txt", fname )
        if len(waveformId) == 0: continue 
        self._waveformIds.append ( int(waveformId[0]) ) 

      self._waveformIds = list ( set ( self._waveformIds ) ) 
      


      #Controllo lunghezza file, se ci sono file con lunghezza diversa, il processo si arresta

      if checklength==True:
        self._n_prese,outliers=len_check(self._files)
        files1=np.array(self._files)

        if len(outliers)!=nfiles:
          self._files=files1[outliers]
          nfiles=len(self._files)
        self._n_prese=int(self._n_prese)

      else:
        df=pd.read_csv ( self._files[0], sep = ',',nrows=2 )
        self._n_prese= int( df['Waveform'][0] )

      

    def run ( self,  daq_time = 0.3 ):
      ## Aspettando che la scheda di acquisizione acquisisca un po' di waveform
      time.sleep ( daq_time ) 

      ## Numero random di acquisizioni in un intervallo di un secondo 
      nAcq =1 #np.random.poisson ( 3. ) 

      if nAcq > ( len (self._waveformIds) ):
        return (np.empty ( (0,  self._n_prese )), 
                np.empty ( (0, self._n_prese )),
                np.empty ( (0, self._n_prese )))

      t = np.zeros (  (nAcq,  self._n_prese ))
      C1 = np.zeros ( (nAcq, self._n_prese ))
      C2 = np.zeros ( (nAcq, self._n_prese ))

      acq_this_round = np.random.choice(self._waveformIds, nAcq, replace=False) 
      print (len(self._waveformIds)) 
      
      for iRow, iAcq in enumerate(acq_this_round):
        for channel, channelName in [ (1, 'C1'), (2, 'C2') ]:
          for filename in self._files: 
            if 'C%dTrace%05d' % (channel, iAcq) not in filename:
                continue 


            #Controllo validità file e numero di file
            #Raccolta in memoria dei contenuti dei file

            df = pd.read_csv ( filename, sep = ',', header = 4 )

            if len(df['Time'].values)!=self._n_prese:      
              print ("File non valido (Numero errato di dati): " % filename)
              continue

            t[iRow] = df['Time'].values / 1e-6
            if channel == 1:
              C1  [iRow] = df['Ampl'].values / 1e-3  
            elif channel == 2:
              C2  [iRow] = df['Ampl'].values / 1e-3 

      #Stampa di controllo  
      for acq in acq_this_round: 
        self._waveformIds.remove ( acq ) 

      return t*1000, C1, C2



if __name__ == '__main__':
    acquisitionMananger = FakeWaveformReader ("/home/lucio/timespotwp2_cce_measurement/LucaData/Agosto31/C?Trace*.txt")

    while True: 
        try:
            
            t, C1, C2 = acquisitionMananger.run()
            
            plt.scatter(t[:],C1[:])
            plt.show()
            print(C1.shape)
            print ("Reading... %d waveforms" % t.shape[0]) 
        except StopIteration:
            break 










