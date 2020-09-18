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
from bokeh.models import Slider,Button,Select
from bokeh.io import curdoc



from tqdm import tqdm 

#LETTURA DA FILE
#--------------------------------------------------------------------------------------------------------------------------------------

def readfiles(checklength=False,channel_select=0):

  ''' Legge i file delle prese dati e li trasferisce in memoria sotto gli array t, C1, C2
  
      Se si desidera controllare che tutti i file abbiano la stessa lunghezza, impostare checklenght=True '''


  #files = glob("timespotwp2_cce_measurement/LucaData/Agosto31/C?Trace*.txt")
  files= glob("/home/timespot/timespotwp2_cce_measurement/LucaData/Agosto31/C?Trace*.txt")
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
        pf,pcov=optimize.curve_fit(gauss_asimm,t[i,::step],C1_sm[::step],p0=[-22,1.5,0.5,0.5,1])
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
          pf,pcov=optimize.curve_fit(gauss_skew,t[i,::step],C1_sm[::step],p0=[30 ,1.4 ,1.5 , 10,0.0])
        except:
          print('Errore a ',i)

        #parte di ricerca del minimo
        
        A=optimize.minimize(gauss_skew,1.4,args=(pf[0],pf[1],pf[2],pf[3],pf[4]))

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
  A0h,A0e=np.histogram(A,bins=100,range=(0.1,100))
  if method==0:
    pf,pcov=optimize.curve_fit(just_moyal,A0e[:-1],A0h,p0=[5000,17.0,10.0])
    A0hfit=just_moyal(A0e[:-1],pf[0],pf[1],pf[2])
  elif method==1:
    pf,pcov=optimize.curve_fit(moyalangauss,A0e[:-1],A0h,p0=[5000.0 , 0, 17.0, 0.0, 10,0.1])

    A0hfit=moyalangauss(A0e,pf[0],pf[1],pf[2],pf[3],pf[4],pf[5])
  return A0h,A0e,A0hfit,pf,pcov

#METODI PER PLOTTARE I FIT
#---------------------------------------------------------------------------------------------------------------------------

def make_plot(title, hist, edges):
    p = figure(title=title, tools='crosshair,pan,reset,save,wheel_zoom', background_fill_color="#fafafa")
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
           fill_color="blue", line_color="white", alpha=0.5,legend_label='')
    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.xaxis.axis_label = 'Ampiezze (mV)'
    p.yaxis.axis_label = 'N prese dati'
    p.grid.grid_line_color="white"
    return p


def make_plot2(title, hist, edges, x, pdf):
    p = figure(title=title, tools="crosshair,pan,reset,save,wheel_zoom", background_fill_color="#fafafa")
    p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:],
           fill_color="navy", line_color="white", alpha=0.5)
    p.line(x, pdf, line_color="#ff8888", line_width=4, alpha=0.7, legend_label="Landau")

    p.y_range.start = 0
    p.legend.location = "center_right"
    p.legend.background_fill_color = "#fefefe"
    p.xaxis.axis_label = 'Ampiezza (mV)'
    p.yaxis.axis_label = 'N prese dati'
    p.grid.grid_line_color="white"
    return p



 


t,C1,C2=readfiles(channel_select=1)
A0,mu0,B0=Amplitude_dist(t,C1,mode=0,nfiles=0)
A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
p=make_plot('Istogramma 0',A0h,A0e)

def update_button0():
  A0h,A0e,A0hfit,p0,p0cov=fit_hist(A0,method=0)
  p.line(A0e[:-1], A0hfit, line_color="#ff8888", line_width=4, alpha=0.7, legend_label="Landau")
def update_button1():
  A0h,A0e,A0hfit,p0,p0cov=fit_hist(A0,method=1)
  p.line(A0e[:-1], A0hfit, line_color="green", line_width=4, alpha=0.7, legend_label="Landau + Gaussiana")

def update_menu(attr,old,new):

  if menu.value=='Gaussiana biforcuta':
    #p.title.text='Attendere ...'
    A0,mu0,B0=Amplitude_dist(t,C1,mode=0,nfiles=0)
    A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
    p=make_plot('Istogramma 0',A0h,A0e)
  elif menu.value=='Gaussiana skew':
    #p.title.text='Attendere ...'
    A0,mu0,B0=Amplitude_dist(t,C1,mode=1,nfiles=0)
    A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
    p=make_plot('Istogramma 0',A0h,A0e)
  elif menu.value=='Ricerca minimi semplice':
    #p.title.text='Attendere ...'
    A0,mu0,B0=Amplitude_dist(t,C1,mode=2,nfiles=0)
    A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
    p=make_plot('Istogramma 0',A0h,A0e)





 
bottone0=Button(label='Fit con solo Landau')
bottone1=Button(label='Fit con Landau+Gaussiana')
menu=Select(options=['Gaussiana biforcuta','Gaussiana skew','Ricerca minimi semplice'],value='Gaussiana biforcuta',title='Fit delle singole prese dati')

menu.on_change('value',update_menu)
bottone0.on_click(update_button0)
bottone1.on_click(update_button1)
fitting_buttons=column(bottone0,bottone1,menu)
#output_notebook()
curdoc().add_root(row(fitting_buttons, p, width=800))
curdoc().title = "Istogramma"
