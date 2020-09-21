import numpy as np
from scipy import special
from scipy import stats
from scipy import integrate



#Fitting per la waveform
#---------------------------------------------------------------------------------------------------------------------------------------------

class UsefulFunctions: 
    def __init__(self):
        print('Module ready')

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
    #-------------------------------------------------------------------------------------------------

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
        '''trasforma l'output "edges" della funzione np.hist in un formato utilizzabile dalle altre funzioni'''
        n=len(edges)-1
        realedges=np.zeros(n)
        for i in range(n):
            realedges[i]=(edges[i]+edges[i+1])*0.5
        return realedges