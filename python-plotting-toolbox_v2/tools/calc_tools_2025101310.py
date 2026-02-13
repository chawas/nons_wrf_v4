import numpy as np

g0 = 9.80665
R0 = 287.058 #J/(kg*K)
Cp = 1004.0 #J/(kg*K)
Cv = 717 #J/(kg*K)


def potential_temperature(T, p):

    p0 = 100000.0  # Pa
    p = p * 100.0  # -> Pa
    T = T + 273.15

    theta = T * (p0 / p ) ** (R0 / Cp)

    return theta

def entropy(theta):

    Phi = Cp * np.log(theta)

    return Phi

def windDirFromVect(u,v):
     a = np.arctan(1.)*4./180. #Constant for wdir calculation
     wd = 180 + np.arctan2(u,v)/a
     ws = np.hypot(u, v)
     return wd

### FUNCTIONS FOR CALCULATING THE DEW POINT, Td ###
        ### from Wikipedia/NOAA ###
def Gamma(T,RH):
    b = 17.67
    c = 243.5 #Celsius
    gamma = np.log(RH) + ( (b*(T)) / (c + (T)))
    return gamma

def dewT(T,RH):
    b = 17.67
    c = 243.5 #Celsius
    Td = (c * Gamma(T,RH)) / (b - Gamma(T,RH))
    return Td
