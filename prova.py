#t,C1,C2=readfiles(channel_select=1)
#A0,mu0,B0=Amplitude_dist(t,C1,mode=0,nfiles=0)
#A0h,A0e=np.histogram(A0,range=(0.1,100),bins=100)
A0=np.zeros(100)
A0h=np.ones(100)
A0e=np.linspace(0,100,101,endpoint=1)
source=ColumnDataSource(data=dict(hist=A0h,edges1=A0e[:-1],edges2=A0e[1:]))
source2=ColumnDataSource(data=dict(x1=np.zeros(100),y1=np.zeros(100)))
p=make_plot('Istogramma 0',A0h,A0e,source)
acquisizione=False

def update_button0():

  A0h,A0e,A0hfit,p0,p0cov=fit_hist(A0,method=0)
  source2.data=dict(x1=A0e[:-1],y1=A0hfit)
  p.line('x1','y1' ,source=source2 ,line_color="#ff8888", line_width=4, alpha=0.7, legend_la$
def update_button1():

  A0h,A0e,A0hfit,p0,p0cov=fit_hist(A0,method=1)
  source2.data=dict(x1=A0e[:-1],y1=A0hfit)
  p.line('x1','y1',source=source2 ,line_color="green", line_width=4, alpha=0.7, legend_label$

def update_button2():

  global acquisizione
  if acquisizione==False:
    print ('Inizio acq')
    acquisizione=True
    bottone2.update(label='Stop',button_type='danger')
  else:
    acquisizione=False

    print ('Stop')

    bottone0.update(visible=True)
    bottone1.update(visible=True)
    bottone2.update(label='Inizio acquisizione',button_type='success')

def ciclo_acq():

  if acquisizione==True:

    print ('acquisendo...')


    acquisitionMananger = WaveformReader ("/home/timespot/timespotwp2_cce_measurement/LucaDa$
    dbw = DatabaseWrite('waveforms.db', acquisitionMananger)
    dbw.run()
def update_menu(attr,old,new):

  global A0

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


bottone0=Button(label='Fit con Landau',visible=False)
bottone1=Button(label='Fit con Landau+Gaussiana',visible=False)
bottone2=Button(label='Iniziare presa misure',button_type='success')
menu=Select(options=['Gaussiana biforcuta','Gaussiana skew','Ricerca minimi semplice'],value$

menu.on_change('value',update_menu)
bottone0.on_click(update_button0)
bottone1.on_click(update_button1)
bottone2.on_click(update_button2)

fitting_buttons=column(bottone2,bottone0,bottone1,menu)


curdoc().add_root(row(fitting_buttons, p, width=800))
curdoc().add_periodic_callback(ciclo_acq, 1000)
curdoc().title = "Istogramma"
