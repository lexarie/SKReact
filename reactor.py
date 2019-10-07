#!/usr/bin/env python

__author__ = "Alex Goldsack"

""" 
The portion of SKReact dealing with neutrino production in
nuclear reactors and subsequent oscillation.
"""

import params
from params import *
import pandas
from math import sin, cos, tan, sqrt, radians
from calendar import monthrange
import numpy as np
import math

# List of energies we do calcs with
# Offset to be centre of bins
# energies = np.linspace(E_MIN+E_INTERVAL/2, 
#     E_MAX+E_INTERVAL/2, 
#     E_BINS,
#     endpoint=False)
energies = np.linspace(E_MIN, 
    E_MAX, 
    E_BINS,
    endpoint=False)

# Calculating xsec for each energy
e_e = lambda e: e - DEL_NP
p_e = lambda e: math.sqrt(e_e(e)**2 - M_E*M_E)
e_exp = lambda e: e**(-0.07056+0.02018*math.log(e)-0.001953*(math.log(e))**3)
xsec = lambda e: 1e-43*p_e(e)*e_e(e)*e_exp(e) # cm^2

# Set up list of xsecs for set of energies
xsecs = []
for energy in energies:
    if (energy > IBD_MIN):
        xsecs.append(xsec(energy))
    else:
        xsecs.append(0.0)

class Reactor:

    # Initialiser
    def __init__(self,
            country,
            name,
            latitude,
            longitude,
            core_type,
            mox,
            p_th,
            lf_monthly,
            default=True):

        self.country = country
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        #core_type is checked later, need to remove whitespace
        self.core_type = core_type.rstrip()
        self.mox = mox
        self.p_th = p_th # MW
        self.dist_to_sk = self._dist_to_sk()
        self.lf_monthly = lf_monthly #Pandas series
        self.p_monthly = self._p_monthly()
        self.p_r_monthly = self._p_r_monthly()
        self.default = default # If the reactor came from the xls
        self.e_spectra = self._e_spectra() # Produced

    # Monthly power output calculate from load factor and p_th
    def _p_monthly(self):
        # Same format as lf
        index = self.lf_monthly.index 
        p_list = [self.p_th*lf for lf in self.lf_monthly.tolist()]
        return pd.Series(p_list, index=index)

    # Monthly power/r^2 output calculate from p_monthly and dist_to_sk
    def _p_r_monthly(self):
        # Same format as lf
        index = self.p_monthly.index 
        p_r_list = [p/(self.dist_to_sk**2) for p in self.p_monthly.tolist()]
        return pd.Series(p_r_list, index=index)

    def add_to_lf(self, date, lf):
        # print(self.name)
        # print(date)
        # print(lf)
        self.lf_monthly.set_value(date, lf)
        self.p_monthly.set_value(date, lf*self.p_th)
        self.p_r_monthly.set_value(date, lf*self.p_th/(self.dist_to_sk**2))
        return

    # Sets on sets on sets 
    def set_country(self, country):
        self.country = country
        return

    def set_name(self, name):
        self.name = name 
        return

    # Need to recalculate dist to sk when changing pos
    def set_latitude(self, latitude):
        self.latitude = latitude 
        self.dist_to_sk = self._dist_to_sk()
        return

    def set_longitude(self, longitude):
        self.longitude = longitude 
        self.dist_to_sk = self._dist_to_sk()
        return

    # Need to reproduce E spec if core type changes
    def set_core_type(self, core_type):
        self.core_type = core_type 
        self.e_spectra = self._e_spectra()
        return

    def set_mox(self, mox):
        self.mox = mox 
        self.e_spectra = self._e_spectra()
        return

    def set_p_th(self, p_th):
        self.p_th = p_th 
        return

    # Should be pd Series, maybe I should assert?
    def set_lf_monthly(self, lf_monthly):
        self.lf_monthly = lf_monthly 
        self.p_monthly = self._p_monthly()
        self.p_r_monthly = self._p_r_monthly()
        return

    # Calculate the number of neutrinos produced in given period
    # CURRENT STATE IS DEPRICATED, CANNOT GUARANTEE IT PRODUCES GOOD NUMBERS
    # TODO: Move the common calcs outside the if statement
    def n_nu(self, period = "Max"):
        # Pre-calculating the nu per second at reference power for self
        nu_per_s = self.p_th*NU_PER_MW 
        if(period == "Max" or period == "max"): # Yearly at reference P
            return 365*24*60*60*nu_per_s
        elif(len(period) == 15): # Inclusive period YYYY/MM-YYYY/MM
            year_start  = int(period[:4])
            month_start = int(period[5:7])
            year_end  = int(period[8:12])
            month_end = int(period[13:])

            # Cycle through all months calculating nu per month
            month_range_start = month_start
            month_range_end = 13
            n_nu_tot = 0
            for year in range(year_start,year_end+1):
                # Start from Jan after first year
                if(year != year_start):
                    month_range_start = 1
                # Only go up to end of period in final year
                if(year == year_end):
                    month_range_end = month_end+1 # For inclusivity
                for month in range(month_range_start,month_range_end):
                    n_days_in_month = monthrange(year,month)[1]
                    # Query the specific month from the LF series
                    lf_month = self.lf_monthly["%i/%02i" % (year, month)]
                    lf_month /= 100 #To be a factor, not %age
                    n_nu_month = (n_days_in_month*24*60*60)
                    n_nu_month *= (lf_month*nu_per_s)

                    n_nu_tot += n_nu_month

            return n_nu_tot
        elif(len(period) == 7): # Specific month YYYY/MM
            year  = int(period[:4])
            month = int(period[5:])
            n_days_in_month = monthrange(year,month)[1]
            lf_month = self.lf_monthly["%i/%02i" % (year, month)]
            lf_month /= 100
            n_nu_month = (n_days_in_month*24*60*60)
            n_nu_month *= (lf_month*nu_per_s)
            return n_nu_month
        elif(len(period) == 4): # Specific year YYYY
            year = int(period)

            # Cycle through all months calculating nu per month
            n_nu_tot = 0
            for month in range(1,13):
                n_days_in_month = monthrange(year,month)[1]
                # Query the specific month from the LF series
                lf_month = self.lf_monthly["%i/%02i" % (year, month)]
                lf_month /= 100

                n_nu_month = (n_days_in_month*24*60*60)
                n_nu_month *= (lf_month*nu_per_s)

                n_nu_tot += n_nu_month

            return n_nu_tot
        else:
            print("reactor.n_nu() requires either YYYY/MM, YYYY or \"Max\" "
                "(per year) for period of nu production.")
            exit()

    """ 
    Earth bulges a the equator, this gives distance to
    centre of the Earth as a function of latitude
    """
    def _dist_to_earth_centre(self, latitude):
        a = EARTH_R_EQUATOR**2*cos(latitude)
        b = EARTH_R_POLAR**2*sin(latitude)
        c = EARTH_R_EQUATOR*cos(latitude)
        d = EARTH_R_POLAR*sin(latitude)

        r = sqrt((a*a + b*b)/(c*c + d*d))

        return r

    """
    Returns sin of geocentric latitude from geodetic latitude
    """
    def _sin_geocentric(self, latitude):
        tan_a = EARTH_R_POLAR*tan(latitude)/EARTH_R_EQUATOR
        sin_a = tan_a/sqrt(1+tan_a*tan_a)
        return sin_a

    """
    Returns cos of geocentric latitude from geodetic latitude
    """
    def _cos_geocentric(self, latitude):
        tan_a = EARTH_R_POLAR*tan(latitude)/EARTH_R_EQUATOR
        cos_a = 1/sqrt(1+tan_a*tan_a)
        return cos_a

    """
    Use Lat and Long info to calc distance to SK in km
    Assume reactors are at sea level, very reasonable
    assumption, given most are on coastline
    """
    def _dist_to_sk(self):
        lat_react_rad = radians(self.latitude)
        long_react_rad = radians(self.longitude)

        lat_sk_rad = radians(SK_LAT)
        long_sk_rad = radians(SK_LONG)

        r_react = self._dist_to_earth_centre(lat_react_rad)
        r_sk    = self._dist_to_earth_centre(lat_sk_rad) + SK_ALT

        x_react = r_react*self._cos_geocentric(lat_react_rad)*cos(long_react_rad)
        y_react = r_react*self._cos_geocentric(lat_react_rad)*sin(long_react_rad)
        z_react = r_react*self._sin_geocentric(lat_react_rad)

        x_sk = r_sk*self._cos_geocentric(lat_sk_rad)*cos(long_sk_rad)
        y_sk = r_sk*self._cos_geocentric(lat_sk_rad)*sin(long_sk_rad)
        z_sk = r_sk*self._sin_geocentric(lat_sk_rad)

        dist = sqrt((x_react-x_sk)**2 + (y_react-y_sk)**2 + (z_react-z_sk)**2)
        
        return dist

    """
    Getting E spectrum from 5th order polynomial for given coefficients
    """
    def _f_from_poly(self,energy,coeffs):
        flux = 0
        for i,a in enumerate(coeffs):
            flux += a*energy**i

        return math.exp(flux)

    """
    Use 5th order polynomial to simulate E spectrum produced by reactors,
    taking into account reactor type and whether the reactor uses MOX
    NOTE: The spectrum produced is PER SECOND at reference power p_th
    """
    def _e_spectra(self):
        core_type = self.core_type
        if(self.mox):
            core_type = "MOX"

        # Fuel fractions for this type of core (p_i in literature)
        u_235_frac = FUEL_MAKEUP.loc[core_type]["U_235"]
        pu_239_frac = FUEL_MAKEUP.loc[core_type]["Pu_239"]
        u_238_frac = FUEL_MAKEUP.loc[core_type]["U_238"]
        pu_241_frac = FUEL_MAKEUP.loc[core_type]["Pu_241"]

        # P is in MW Q is in MeV, so change Q to MJ
        u_235_prefactor = self.p_th*u_235_frac/(U_235_Q*EV_J)
        pu_239_prefactor = self.p_th*pu_239_frac/(PU_239_Q*EV_J)
        u_238_prefactor = self.p_th*u_238_frac/(U_238_Q*EV_J)
        pu_241_prefactor = self.p_th*pu_241_frac/(PU_241_Q*EV_J)
        u_235_spectrum = [u_235_prefactor*self._f_from_poly(energy,U_235_A)
                for energy in energies]
        pu_239_spectrum = [pu_239_prefactor*self._f_from_poly(energy,PU_239_A) 
                for energy in energies]
        u_238_spectrum = [u_238_prefactor*self._f_from_poly(energy,U_238_A) 
                for energy in energies]
        pu_241_spectrum = [pu_241_prefactor*self._f_from_poly(energy,PU_241_A) 
                for energy in energies]
        tot_spectrum = [sum(f) for f in zip(
            u_235_spectrum, 
            pu_239_spectrum, 
            u_238_spectrum, 
            pu_241_spectrum)]

        spectrum_data = {
                "U_235": u_235_spectrum,
                "Pu_239": pu_239_spectrum,
                "U_238": u_238_spectrum,
                "Pu_241": pu_241_spectrum,
                "Total" : tot_spectrum}

        e_spectra = pd.DataFrame(spectrum_data, index=energies)

        return e_spectra

    """
    Produces tuple of up and down errors of e spectra, calculated
    by finding the max and min values and their diff from the mean
    """
    def _e_spectra_err(self):
        core_type = self.core_type
        if(self.mox):
            core_type = "MOX"

        # Fuel fractions for this type of core (p_i in literature)
        u_235_frac = FUEL_MAKEUP.loc[core_type]["U_235"]
        pu_239_frac = FUEL_MAKEUP.loc[core_type]["Pu_239"]
        u_238_frac = FUEL_MAKEUP.loc[core_type]["U_238"]
        pu_241_frac = FUEL_MAKEUP.loc[core_type]["Pu_241"]

        # P is in MW Q is in MeV, so change Q to MJ
        u_235_prefactor = self.p_th*u_235_frac/(U_235_Q*EV_J)
        pu_239_prefactor = self.p_th*pu_239_frac/(PU_239_Q*EV_J)
        u_238_prefactor = self.p_th*u_238_frac/(U_238_Q*EV_J)
        pu_241_prefactor = self.p_th*pu_241_frac/(PU_241_Q*EV_J)

        # Maximum coeffs
        u_235_a_up = [a+da for a,da in zip(U_235_A,U_235_DA)]
        pu_239_a_up = [a+da for a,da in zip(PU_239_A,PU_239_DA)]
        u_238_a_up = [a+da for a,da in zip(U_238_A,U_238_DA)]
        pu_241_a_up = [a+da for a,da in zip(PU_241_A,PU_241_DA)]

        u_235_spec_up = [u_235_prefactor*self._f_from_poly(energy,
            u_235_a_up)
            for energy in energies]
        pu_239_spec_up = [pu_239_prefactor*self._f_from_poly(energy,
            pu_239_a_up)
            for energy in energies]
        u_238_spec_up = [u_238_prefactor*self._f_from_poly(energy,
            u_238_a_up)
            for energy in energies]
        pu_241_spec_up = [pu_241_prefactor*self._f_from_poly(energy,
            pu_241_a_up)
            for energy in energies]
        tot_spec_up = [sum(f) for f in zip(
            u_235_spec_up, 
            pu_239_spec_up, 
            u_238_spec_up, 
            pu_241_spec_up)]

        # Minimum coeffs
        u_235_a_down = [a-da for a,da in zip(U_235_A,U_235_DA)]
        pu_239_a_down = [a-da for a,da in zip(PU_239_A,PU_239_DA)]
        u_238_a_down = [a-da for a,da in zip(U_238_A,U_238_DA)]
        pu_241_a_down = [a-da for a,da in zip(PU_241_A,PU_241_DA)]

        u_235_spec_down = [u_235_prefactor*self._f_from_poly(energy,
            u_235_a_down)
            for energy in energies]
        pu_239_spec_down = [pu_239_prefactor*self._f_from_poly(energy,
            pu_239_a_down)
            for energy in energies]
        u_238_spec_down = [u_238_prefactor*self._f_from_poly(energy,
            u_238_a_down)
            for energy in energies]
        pu_241_spec_down = [pu_241_prefactor*self._f_from_poly(energy,
            pu_241_a_down)
            for energy in energies]
        tot_spec_down = [sum(f) for f in zip(
            u_235_spec_down, 
            pu_239_spec_down, 
            u_238_spec_down, 
            pu_241_spec_down)]

        spec_up_data = {
                "U_235": u_235_spec_up,
                "Pu_239": pu_239_spec_up,
                "U_238": u_238_spec_up,
                "Pu_241": pu_241_spec_up,
                "Total" : tot_spec_up}
        spec_down_data = {
                "U_235": u_235_spec_down,
                "Pu_239": pu_239_spec_down,
                "U_238": u_238_spec_down,
                "Pu_241": pu_241_spec_down,
                "Total" : tot_spec_down}

        e_spec_up_tot = pd.DataFrame(spec_up_data, index=energies)
        e_spec_down_tot = pd.DataFrame(spec_down_data, index=energies)

        e_spec_up_err = e_spec_up_tot.subtract(self.e_spectra)
        e_spec_down_err = self.e_spectra.subtract(e_spec_down_tot)

        return e_spec_up_err,e_spec_down_err 

    """
    Calculating the spectrum of ALL oscillated nu E at SK
    """
    #TODO: Add in hierarchy support (I think it barely changes it)
    def oscillated_spec(self,
            dm_21 = DM_21,
            c_13 = C_13_NH,
            s_2_12 = S_2_12,
            s_13 = S_13_NH,
            period = "Max"):

        # Finding total load factor 
        year_start  = int(period[:4])
        month_start = int(period[5:7])
        year_end  = int(period[8:12])
        month_end = int(period[13:])

        # Cycle through all months summing load factor*t 
        lf_sum = 0
        month_range_start = month_start
        month_range_end = 13
        n_nu_tot = 0
        for year in range(year_start,year_end+1):
            # Start from Jan after first year
            if(year != year_start):
                month_range_start = 1
            # Only go up to end of period in final year
            if(year == year_end):
                month_range_end = month_end+1 # For inclusivity
            for month in range(month_range_start,month_range_end):
                n_days_in_month = monthrange(year,month)[1]
                # Query the specific month from the LF series
                # print(self.lf_monthly)
                try:
                    lf_month = float(self.lf_monthly["%i/%02i" % (year, month)])
                except TypeError:
                    print("Load factor data for reactor "
                            + self.name
                            + " in month %i/%02i" % (year,month)
                            + " not float compatible")
                    exit()
                except KeyError:
                    print("Error with " 
                            + self.name 
                            + " in or around file DB%i.xls" % year)
                    print("Does not have entry for this year.")
                    exit()
                lf_month /= 100 #To be a factor, not %age
                lf_sum += lf_month*n_days_in_month

        # lf_sum is sum of monthly load factors, so
        # p_th*lf_sum*(seconds in month) is integrated power
        # months had to do in sum cause months are stupid
        spec_pre_factor = lf_sum*24*60*60
        # From PHYSICAL REVIEW D 91, 065002 (2015)
        # E in MeV, l in km
        l = self.dist_to_sk
        p_ee = lambda e: c_13*c_13*(1-s_2_12*(math.sin(1.27*dm_21*l*1e3/e))**2)+s_13*s_13

        # Don't think I'll need osc. spectra of individual fuels
        e_spec = self.e_spectra["Total"].tolist()
        osc_e_spec = []
        for f,e in zip(e_spec,energies):
            if(e > IBD_MIN):
                # Calc flux by dividing by area of sphere at l (m)
                osc_e_spec.append(spec_pre_factor*f*p_ee(e)/(4*math.pi*(l*1e3)**2))
            else:
                osc_e_spec.append(0)
        osc_spec = pd.Series(osc_e_spec, index=energies)
        return osc_spec

    """
    Spectrum of INCIDENT oscillated nu E at SK
    Takes oscillated spec as list and multiplies by xsec
    """
    def incident_spec(self,
            osc_spec):
        # From PHYSICAL REVIEW D 91, 065002 (2015)
        incident_spec_dat = []
        # for xsec,f in zip(xsecs,osc_spec):
        i = 0
        for energy,f in osc_spec.iteritems():
            # 1e-4 because xsec is in cm^2
            incident_spec_dat.append(FLUX_SCALE*f*xsecs[i]*(1e-4)*SK_N_P)
            i+=1

        incident_spec = pd.Series(incident_spec_dat, 
            index = energies,
            name = self.name)

        return incident_spec
