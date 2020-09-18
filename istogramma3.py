#Ora, tutto, ma più bokrh-friendly
import pandas as pd
from glob import glob 
import numpy as np
import re
from scipy import optimize
from scipy import special
from scipy import integrate
from scipy import stats
import matplotlib.pyplot as plt
from scipy.signal import butter,lfilter
from scipy.ndimage import gaussian_filter
from time import time
from bokeh.layouts import gridplot,column,row
from bokeh.plotting import figure, output_file, show,output_notebook
from bokeh.models import Slider,Button,Select,ColumnDataSource,Paragraph
from bokeh.io import curdoc
from DatabaseWriter import DatabaseWrite
from WaveformReader import WaveformReader
from tqdm import tqdm 

#LETTURA DA FILE
#--------------------------------------------------------------------------------------------------------------------------------------

def readfiles(checklength=False,channel_select=0):

  ''' Legge i file delle prese dati e li trasferisce in memoria sotto gli array t, C1, C2
  
      Se si desidera controllare che tutti i file abbiano la stessa lunghezza, impostare checklenght=True '''


  files = glob("/home/lucio/timespotwp2_cce_measurement/LucaData/Agosto31/C?Trace*.txt")
  #files= glob("/home/timespot/timespotwp2_cce_measurement/LucaData/Agosto31/C?Trace*.txt")
  nfiles=len(files)

  #Controllo lunghezza file, se ci sono file con lunghezza diversa, il processo si arresta

  if checklength==True:
    n_prese,outliers=len_check(files)
    files1=np.array(files)

    if len(outliers)!=nfiles:
      files=files1[outliers]
      nfiles=len(files)
    n_prese=int(n_prese)

  else:
    df=pd.read_csv ( files[0], sep = ',',nrows=2 )
    n_prese= int( df['Waveform'][0] )

  #if filelimit!=0:
   # files=files[:(filelimit)]
    #nfiles=filelimit



  
  #Inizializzazione array

  t = np.zeros ( (nfiles//2+1, n_prese ))
  C1 = np.zeros ( (nfiles//2+1, n_prese ))
  C2 = np.zeros ( (nfiles//2+1, n_prese ))



  for filename in tqdm(files, unit = 'files'):

    #Controllo validità file e numero di file

    channel = re.findall (r"timespotwp2_cce_measurement/LucaData/Agosto31/C([0-9])Trace.*\.txt", filename )
    if len(channel) == 0:
      print ("File non valido (channel not found): " % filename)
      continue 
    channel = int (channel[0])

    #Controllo canale selezionato

    if channel_select!=0:
      if channel!=channel_select:
        continue




    waveform = re.findall (r"timespotwp2_cce_measurement/LucaData/Agosto31/C[0-9]Trace([0-9]*)\.txt", filename )
    if len(waveform) == 0:
      print ("File non valido (waveform not found): " % filename)
      continue 
    waveform = int (waveform[0])

    #Raccolta in memoria dei contenuti dei file
    
    df = pd.read_csv ( filename, sep = ',', header = 4 )

    if len(df['Time'].values)!=n_prese:      
      print ("File non valido (Numero errato di dati): " % filename)
      continue


    t[waveform] = df['Time'].values / 1e-6

    if channel == 1:
      C1  [waveform] = df['Ampl'].values / 1e-3  
    elif channel == 2:
      C2  [waveform] = df['Ampl'].values / 1e-3 

  #Stampa di controllo

  print ("\n")
  print (t.shape)
  print (C1.shape)
  print (C2.shape)

  return t, C1, C2


#Fitting per la waveform
#---------------------------------------------------------------------------------------------------------------------------------------------



def gauss_asimm ( t, A, mu, s1, s2, baseline ):

  gaus1 = np.exp ( - 0.5*(t - mu)**2/s1**2 )
  gaus2 = np.exp ( - 0.5*(t - mu)**2/s2**2 )
  return -A * np.where ( t < mu, gaus1, gaus2 ) + baseline

def ExMG(t, A, mu, s, tau,baseline):

  tmu=t-mu
  return -A * np.exp(-0.5*(tmu/s)**2)/(1+tmu*tau/s**2) + baseline

def ExMG2(t, A, mu, s, tau,baseline):
  tmus=(t-mu)/s
  stau=s/tau
  return -A * np.exp(-0.5*tmus**2)*np.sqrt(np.pi*0.5)*special.erf(1/np.sqrt(2)*(stau-tmus))+baseline

def gauss_skew(t, A, mu, s, alpha, baseline):
  tmus=(t-mu)/s 
  return -A*np.exp(-0.5*tmus**2)*(0.5*(1.0+special.erf(alpha/np.sqrt(2)*tmus)))+baseline


#Fitting per l'istogramma
#----------------------------------------------------------------------------------------------------------------------------------------------------------



def landau_appr(t,A,mu):
  return A*np.exp(-0.5*((t-mu)-np.exp(-t+mu)))

def landau(tim,A,mu,s):

  out=np.zeros(len(tim))

  for i,t in enumerate(tim):
    t2=(t-mu)*s
    inte,interr=integrate.quad(landau2,0,np.inf,args=(t2))
    out[i]=A*inte

  return out

def landau2(x,t):
  return np.exp(-x*np.log(x)-x*t)*np.sin(np.pi*x)

def moyalangauss(edges,A1,A2,mu1,mu2,s1,s2 ):
  m=stats.moyal()
  mo=stats.moyal.pdf(edges,loc=mu1,scale=s1)*A1
  gauss=A2*np.exp(-0.5*(edges-mu2)**2/s2**2)
  return mo+gauss
def just_moyal(edges,A1,mu1,s1):
  m=stats.moyal()
  return stats.moyal.pdf(edges,loc=mu1,scale=s1)*A1


def gaussanmoyal(edges,A1,A2,mu1,mu2,s1,s2,div):
  m=stats.moyal()
  mo=stats.moyal.pdf(edges,loc=mu1,scale=s1)*A1
  gauss=A2*np.exp(-0.5*(edges-mu2)**2/s2**2)
  return np.where(edges<div,gauss,mo)

def edges_adjust(edges):
  n=len(edges)-1
  realedges=np.zeros(n)
  for i in range(n):
    realedges[i]=(edges[i]+edges[i+1])*0.5
  return realedges


#CALCOLO SISTEMATICO AMPIEZZE GRAFICI
#------------------------------------------------------------------------------------------------------------------------------

def Amplitude_dist(t,C,mode=0,step=50,nfiles=0):

  '''Calcola le ampiezze di un set di misure C prese ognuna con i tempi t, fittandole con 3 diverse modalità:


     mode=0: Gaussiana biforcuta 
     mode=1: Gaussiana "skewed"
     mode=2: Calcolo del minimo a partire dai dati filtrati
     
     Stampa a schermo ogni volta che non è stato possibile eseguire un fit
     
     L'argomento "step" indica la frequenza con cui il programma esegue il fit
     
     Per le mode 0 e 1 la funzione porta in output le ampiezze, lo spostamento mu, e la baseline di ogni presa dati. 
     Per la mode 2 porta in ouput solo le ampiezze   '''

  #inizializzazione array

  n=len(C)
  if nfiles!=0:
    right_files=np.random.randint(0,n,size=nfiles)
    C1=C[right_files]
    n=nfiles
  else:
    C1=np.copy(C)
    
  Amplitude=np.zeros(n)
  mu=np.zeros(n)
  baseline=np.zeros(n)
 
  #controllo errori
  if type(step)!=int:
    raise ValueError("L'argomento step deve essere un intero positivo")
  elif step<=0:
    raise ValueError("L'argomento step deve essere un intero positivo")


  if mode==0:

    # modalità gaussiana biforcuta

    for i in tqdm(range(n)):
      pf=np.zeros(5)
      C1_sm=gaussian_filter(C1[i],40)
      try:
        pf,pcov=optimize.curve_fit(gauss_asimm,t[i,::step],C1_sm[::step],p0=[22,15,1,1,1])
      except:
        print('Errore a ',i)

      Amplitude[i]=pf[0]
      mu[i]=pf[1]
      baseline[i]=pf[4]

  elif mode==1:

    #modalità gaussiana skewed

      for i in tqdm(range(n)):

        pf=np.zeros(5)
        C1_sm=gaussian_filter(C1[i],40)

        #parte di fitting

        try:
          pf,pcov=optimize.curve_fit(gauss_skew,t[i,::step],C1_sm[::step],p0=[30 ,14 ,1.5 , 10,0.0])
        except:
          print('Errore a ',i)

        #parte di ricerca del minimo
        
        A=optimize.minimize(gauss_skew,14,args=(pf[0],pf[1],pf[2],pf[3],pf[4]))

        Amplitude[i]=-A.fun+pf[4]
        mu[i]=A.x 
        baseline[i]=pf[4]

  elif mode==2:

    #modalità ricerca del minimo a partire dai dati filtrati

    for i in tqdm(range(n)):

      C1_sm=gaussian_filter(C1[i],40)
      Amplitude[i]=-np.min(C1_sm)
   
  return Amplitude,mu,baseline 

#METODI PER FITTARE GLI ISTOGRAMMI

def fit_hist(A,method=0):
  A0h,A0e_prov=np.histogram(A,bins=100,range=(0.1,100))
  A0e=edges_adjust(A0e_prov)
  if method==0:
    nmoyal=sum(A0h[7:])
    pf,pcov=optimize.curve_fit(just_moyal,A0e,A0h,p0=[nmoyal,17.0,10.0])
    
    A0hfit=just_moyal(A0e,pf[0],pf[1],pf[2])
  elif method==1:
    ngauss=sum(A0h[:7])
    nmoyal=sum(A0h[7:])
    pf,pcov=optimize.curve_fit(moyalangauss,A0e,A0h,p0=[nmoyal, ngauss, 17.0, 1.0, 10,2.0])
  
    
    A0hfit=moyalangauss(A0e,pf[0],pf[1],pf[2],pf[3],pf[4],pf[5])
  elif method==2:
    pf,pcov=optimize.curve_fit(gaussanmoyal,A0e,A0h,p0=[5000.0 , 5, 17.0, 3.0, 10,0.1,5])
    A0hfit=gaussanmoyal(A0e,pf[0],pf[1],pf[2],pf[3],pf[4],pf[5],pf[6])
  return A0h,A0e,A0hfit,pf,pcov


#METODI PER PLOTTARE I FIT
#---------------------------------------------------------------------------------------------------------------------------

def make_plot(title, hist, edges,source):
    p = figure(title=title, tools='crosshair,pan,reset,save,wheel_zoom', background_fill_color="#fafafa")
    p.quad(top='hist',source=source, bottom=0, left='edges1', right='edges2',
           fill_color="blue", line_color="white", alpha=0.5,legend_label='')
    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.xaxis.axis_label = 'Ampiezze (mV)'
    p.yaxis.axis_label = 'N prese dati'
    p.grid.grid_line_color="white"
    return p


def make_plot2(title,source3):
    p = figure(title=title, tools="crosshair,pan,reset,save,wheel_zoom", background_fill_color="#fafafa")
    p.line('t','V',source=source3, line_color="#ff8888", line_width=1, alpha=1, legend_label="Waveform")

    
    p.legend.location = "bottom_left"
    p.legend.background_fill_color = "#fefefe"
    p.yaxis.axis_label = 'Ampiezza (mV)'
    p.xaxis.axis_label = 'Tempo (ns)'
    p.grid.grid_line_color="white"
    return p




#t,C1,C2=readfiles(channel_select=1)
#A0,mu0,B0=Amplitude_dist(t,C1,mode=0,nfiles=0)
#A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
A0=np.zeros(100)#array inizializzati, ampiezze delle singole prese dati
A0h=np.ones(100)#istogramma delle ampiezze
A0e=np.linspace(0,100,100,endpoint=1)#posizione della colonna dell'istogramma
A0h=np.exp(-(A0e[:-1]-50.0)**2/500.0)
source=ColumnDataSource(data=dict(hist=A0h,edges1=A0e[:-1],edges2=A0e[1:]))#source per plottare gli istogrammi
source2=ColumnDataSource(data=dict(x1=np.zeros(100),y1=np.zeros(100)))#source per plottare il fit degli istogrammi
source3=ColumnDataSource(data=dict(t=np.linspace(0,1000,1000),V=np.zeros(1000)))
p=make_plot('Istogramma 0',A0h,A0e,source)#inizializzazione della figura
p2=make_plot2('Attuale presa dati',source3)
acquisizione=False #controlla che il programma stia acquisendo dati, inizializzato a falso
update_menu_check=False
acquisitionMananger = WaveformReader ()
dbw = DatabaseWrite ('waveforms.db', acquisitionMananger) 


#FUNZIONI PER L'AGGIORNAMENTO DEI BOTTONI------------------------------------------------------------------------------------------------


def update_button0():

  '''Bottone per il fitting con la Landau'''

  A0h,A0e,A0hfit,p0,p0cov=fit_hist(A0,method=0)
  source2.data=dict(x1=A0e,y1=A0hfit)
  p.line('x1','y1' ,source=source2 ,line_color="#ff8888", line_width=4, alpha=0.7, legend_label='Fit con Landau')
def update_button1():

  '''Bottone per il fitting della Landau+ la Gaussiana'''

  A0h,A0e,A0hfit,p0,p0cov=fit_hist(A0,method=1)
  source2.data=dict(x1=A0e,y1=A0hfit)
  p.line('x1','y1',source=source2 ,line_color="green", line_width=4, alpha=0.7, legend_label='Fit con Landau+Gaussiana')

def update_button2():

  '''Bottone per l'acquisizione dei dati, controlla l'esecuzione della funzione
ciclo_acq. quando la variabile acquisizione=True
    il programma sta acquisendo dati e il bottone lo ferma, e viceversa
  '''

  global acquisizione,t,C1,update_menu_check
  if acquisizione==False:
    print ('Inizio acq')
    acquisizione=True
    bottone2.update(label='Stop',button_type='danger')
  else:
    acquisizione=False

    print ('Stop')
     
    update_menu_check=True
   # t=np.array(dbw.t)
    #C1=np.array(dbw.C1)
    tlist,C1list,C2list=dbw.readWaveforms()
    C1=np.array(C1list)
    C2=np.array(C2list)
    t=np.array(tlist)
    t=t/1000
    
    bottone0.update(visible=True)
    bottone1.update(visible=True)
    bottone2.update(label='Inizio acquisizione',button_type='success')
    update_menu(0,0,0)


def ciclo_acq():
  global t,C1

  if acquisizione==True:
    t1=time()

    while (time()-t1)<0.8:
      dbw.run() 
   
    t_,C1_,C2_=dbw.readlastWaveform() 

    source3.data=dict(t=t_,V=C1_)
    titolo='Attuale presa dati numero:'+str(dbw.it)
    p2.title.text=titolo
    #t,C1,C2=dbw.readWaveforms()
    #t_=np.array(dbw.t)
    #C1_=np.array(dbw.C1)
    infobox.update(text='Presa misure in corso...')




def update_menu(attr,old,new):

  global A0
  if update_menu_check==False:
    return

  infobox.update(text="Calcolo dell'istogrammma, attendere ...")

  if menu.value=='Gaussiana biforcuta':
    p.title.text='Attendere ...'
    A0,mu0,B0=Amplitude_dist(t,C1,mode=0,nfiles=0)
    A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
    source.data=dict(hist=A0h,edges1=A0e[:-1],edges2=A0e[1:])
    p.title.text='Istogramma 0'

  elif menu.value=='Gaussiana skew':
    p.title.text='Attendere ...'
    A0,mu0,B0=Amplitude_dist(t,C1,mode=1,nfiles=0)
    A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
    source.data=dict(hist=A0h,edges1=A0e[:-1],edges2=A0e[1:])
    p.title.text='Istogramma 0'


  elif menu.value=='Ricerca minimi semplice':
    p.title.text='Attendere ...'
    A0,mu0,B0=Amplitude_dist(t,C1,mode=2,nfiles=0)
    A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
    source.data=dict(hist=A0h,edges1=A0e[:-1],edges2=A0e[1:])
    p.title.text='Istogramma 0'

  infobox.update(text="Programma pronto per iniziare una nuova presa dati")

bottone0=Button(label='Fit con Landau',visible=False)
bottone1=Button(label='Fit con Landau+Gaussiana',visible=False)
bottone2=Button(label='Iniziare presa misure',button_type='success')
menu=Select(options=['Gaussiana biforcuta','Gaussiana skew','Ricerca minimi semplice'],value='Gaussiana biforcuta',title='Fit delle singole prese dati')
infobox=Paragraph(text='Programma pronto per iniziare a prendere misure',width=400)

menu.on_change('value',update_menu)
bottone0.on_click(update_button0)
bottone1.on_click(update_button1)
bottone2.on_click(update_button2)

fitting_buttons=column(bottone2,bottone0,bottone1,menu,infobox)


curdoc().add_root(row(fitting_buttons, p,p2, width=1200))
curdoc().add_periodic_callback(ciclo_acq, 1000)
curdoc().title = "Istogramma"


