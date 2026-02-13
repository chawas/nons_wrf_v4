import numpy as np

# --- Physical constants ---
g0 = 9.80665
R0 = 287.058  # J/(kg*K)
Cp = 1004.0   # J/(kg*K)
Cv = 717.0    # J/(kg*K)

# --- Potential temperature ---
def potential_temperature(T, p):
    """
    Compute potential temperature (K) from temperature (°C) and pressure (hPa).
    """
    p0 = 100000.0  # Reference pressure (Pa)
    p = p * 100.0  # Convert hPa to Pa
    T = T + 273.15  # Convert °C to K

    with np.errstate(divide='ignore', invalid='ignore'):
        theta = T * (p0 / p) ** (R0 / Cp)

    return np.where(np.isfinite(theta), theta, np.nan)

# --- Entropy ---
def entropy(theta):
    """
    Compute entropy (J/kg·K) from potential temperature (K).
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        Phi = Cp * np.log(theta)
    return np.where(np.isfinite(Phi), Phi, np.nan)

# --- Wind direction and speed ---
def windDirFromVect(u, v):
    """
    Compute wind direction (degrees) from u, v components.
    """
    a = np.pi / 180.0  # Constant for degrees
    wd = 180 + np.arctan2(u, v) / a
    ws = np.hypot(u, v)
    return wd

# --- Dew Point Calculations (Improved for numerical safety) ---
def Gamma(T, RH):
    """
    Compute gamma function for dew point formula.
    T in °C, RH as fraction (0-1).
    """
    b = 17.67
    c = 243.5  # °C
    RH = np.clip(RH, 1e-3, 1.0)  # Avoid log(0) or RH > 1

    with np.errstate(divide='ignore', invalid='ignore'):
        gamma = np.log(RH) + (b * T) / (c + T)

    return np.where(np.isfinite(gamma), gamma, np.nan)

def dewT(T, RH):
    """
    Compute dew point temperature (°C) from temperature (°C) and relative humidity (0–1).
    """
    b = 17.67
    c = 243.5  # °C
    RH = np.clip(RH, 1e-3, 1.0)
    gamma_val = Gamma(T, RH)

    with np.errstate(divide='ignore', invalid='ignore'):
        Td = (c * gamma_val) / (b - gamma_val)

    return np.where(np.isfinite(Td), Td, np.nan)
