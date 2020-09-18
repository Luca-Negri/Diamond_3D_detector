from WaveformReader import WaveformReader 

import matplotlib.pyplot as plt
import numpy as np 
import pandas as pd 
import sqlite3 
import base64

class DatabaseWrite:
    def __init__ (self, db_filename, reader):
        self._db = sqlite3.connect ( db_filename ) 
        self.it=0
        self.reader = reader
        self.t=[]
        self.C1=[]
        self.C2=[]
        self._db.execute ( "CREATE TABLE IF NOT EXISTS waveforms (time, c1, c2)" ) 

    def run (self):
        for i in range(1): 
           for i in range(1): #try:
                self.it+=1
                C1list, C2list,tlist = self.reader.run()

                t=np.array(tlist)
                C1=np.array(C1list)
                C2=np.array(C2list)
                nRow = t.shape [ 0 ]
                self.nCol=len(t)
                #print(nRow) 
                if nRow == 0: continue 
                
                for iRow in range (1):
                    encoded_t = base64.b64encode ( t [:].astype(np.float32).tobytes() ) 
                    encoded_1 = base64.b64encode ( C1[:].astype(np.float32).tobytes() ) 
                    encoded_2 = base64.b64encode ( C2[:].astype(np.float32).tobytes() ) 

                    self._db.execute ( "INSERT INTO waveforms (time, c1, c2) VALUES ( ?, ?, ? ) ",
                            (encoded_t, encoded_1, encoded_2) ) 



                ### Leggo l'ultima waveform 
                c = self._db.cursor() 
                c.execute ( "SELECT time, c1, c2 FROM waveforms ORDER BY rowid DESC LIMIT 1" ) 
                for t_, C1_, C2_ in c.fetchall():
                    t_  = np.frombuffer ( base64.b64decode (t_),  dtype = np.float32 )
                    C1_ = np.frombuffer ( base64.b64decode (C1_), dtype = np.float32 )
                    C2_ = np.frombuffer ( base64.b64decode (C2_), dtype = np.float32 )
                    #assert np.all(t_ == t [-1].astype(np.float32) ), "Time array is wrong" 
                    #assert np.all(C1_== C1[-1].astype(np.float32) ), "C1 array is wrong" 
                    #assert np.all(C2_== C2[-1].astype(np.float32) ), "C2 array is wrong" 



             #   print ("Reading... %d waveforms" % t.shape[0]) 
            #except:# StopIteration:
             #   break
             #   print('ERRORE')
    def run2(self):
      for i in range(1):
          C1list, C2list,tlist = self.reader.run()
          self.t.append(tlist)
          self.C1.append(C1list) 
          self.C2.append(C2list)

    def readWaveforms(self):

        c = self._db.cursor() 
        c.execute ( "SELECT time, c1, c2 FROM waveforms" )
        t=[]
        C1=[]
        C2=[]
        for t_, C1_, C2_ in c.fetchall():
            t.append( np.frombuffer ( base64.b64decode (t_),  dtype = np.float32 ))
            C1.append(np.frombuffer ( base64.b64decode (C1_), dtype = np.float32 ))
            C2.append(np.frombuffer ( base64.b64decode (C2_), dtype = np.float32 ))
            #assert np.all(t_ == t [-1].astype(np.float32) ), "Time array is wrong" 
            #assert np.all(C1_== C1[-1].astype(np.float32) ), "C1 array is wrong" 
            #assert np.all(C2_== C2[-1].astype(np.float32) ), "C2 array is wrong" 

        return   t,C1,C2

    def readlastWaveform(self):

      c = self._db.cursor() 
      c.execute ( "SELECT time, c1, c2 FROM waveforms ORDER BY rowid DESC LIMIT 1" ) 
      for t_, C1_, C2_ in c.fetchall():
          t_  = np.frombuffer ( base64.b64decode (t_),  dtype = np.float32 )
          C1_ = np.frombuffer ( base64.b64decode (C1_), dtype = np.float32 )
          C2_ = np.frombuffer ( base64.b64decode (C2_), dtype = np.float32 )

      return t_,C1_,C2_


if __name__ == '__main__':
    acquisitionMananger = WaveformReader ()
    dbw = DatabaseWrite ('waveforms.db', acquisitionMananger) 
    i=0
    while True:
      dbw.run() 
      dbw.run() 
      dbw.run() 
      dbw.run() 
      t,C1,C2=dbw.readWaveforms()
      #t=np.array(dbw.t)
      #C1=np.array(dbw.C1)

      plt.plot(t[1],C1[1])
      plt.show()




