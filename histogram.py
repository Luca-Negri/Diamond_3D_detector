import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput, Button
from bokeh.plotting import figure

from scipy.optimize import curve_fit

from glob import glob
folder =  "/home/timespot/timespotwp2_cce_measurement/LucaData/Agosto31/C*Trace*.txt" 
files = glob (folder) 


data_to_hist = np.random.normal ( 0, 1, 1000 )


plot = figure(plot_height=400, plot_width=400, title="test histogram",
              tools="crosshair,pan,reset,save,wheel_zoom")
              #x_range=[0, 4*np.pi], y_range=[-2.5, 2.5])


hist, edges = np.histogram ( data_to_hist, bins = 100 ) 

def fit_func (x, mean, sigma, amplitude):
    return amplitude/np.sqrt ( 2 * np.pi ) / sigma * np.exp ( -0.5 * (x - mean)**2 / sigma**2 ) 

fx = 0.5*(edges[1:] + edges[:-1]) 

source = ColumnDataSource(data = {
        'y' : hist, 
        'l' : edges[1:],
        'r' : edges[:-1], 
        'b' : np.zeros_like (hist) , 
        'fx': fx, 
        'fy': np.zeros_like ( fx ), 
    })

plot.quad(top = 'y', left = 'l', right = 'r', bottom = 'b', source = source, 
            fill_color = 'navy', line_color = 'white', alpha = 0.5        
            ) 

plot.line ( 'fx', 'fy', source = source, line_color = 'red') 


do_the_fit = Button ( label = "Do the fit!" ) 

def do_the_fit_callback ( ):
    hist, edges = np.histogram ( data_to_hist, bins = 100 ) 
    res, err = curve_fit (fit_func, fx, hist, (0, 1, 1000) ) 
    source.data.update ({'fy' : fit_func(fx, *res)})
    

do_the_fit.on_click ( do_the_fit_callback )  



print (hist) 
curdoc().add_root ( column(plot, do_the_fit) ) 






