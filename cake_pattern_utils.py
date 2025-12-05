# -*- coding: utf-8 -*-
"""
Cake and Pattern View Utilities - Based on Dioptas
Functions for creating cake (polar) views and 1D integration patterns
"""

import numpy as np
import matplotlib.pyplot as plt


def create_cake_image(ai, image, num_chi=360, num_2theta=500):
    """
    Create cake (polar transform) image
    Based on Dioptas cake transformation
    
    Parameters:
    -----------
    ai : AzimuthalIntegrator
        Calibrated integrator object
    image : ndarray
        2D diffraction image
    num_chi : int
        Number of azimuthal bins (default 360)
    num_2theta : int
        Number of radial bins (default 500)
    
    Returns:
    --------
    cake : ndarray
        2D cake image (chi vs 2theta)
    tth_array : ndarray
        2theta values (degrees)
    chi_array : ndarray
        Chi (azimuthal) values (degrees)
    """
    try:
        # Perform 2D integration to create cake
        # This is the Dioptas-style approach
        cake, tth_array, chi_array = ai.integrate2d(
            image,
            npt_rad=num_2theta,
            npt_azim=num_chi,
            unit="2th_deg",
            correctSolidAngle=True
        )
        
        # Convert to degrees
        tth_array = np.degrees(tth_array) if tth_array[0] < 1 else tth_array
        chi_array = np.degrees(chi_array) if chi_array[0] < 1 else chi_array
        
        return cake, tth_array, chi_array
    except Exception as e:
        print(f"Error creating cake image: {e}")
        return None, None, None


def create_pattern(ai, image, num_points=2048, unit="2th_deg"):
    """
    Create 1D integrated pattern
    Based on Dioptas 1D integration
    
    Parameters:
    -----------
    ai : AzimuthalIntegrator
        Calibrated integrator object
    image : ndarray
        2D diffraction image
    num_points : int
        Number of points in 1D pattern (default 2048)
    unit : str
        Unit for x-axis ("2th_deg", "q_A^-1", etc.)
    
    Returns:
    --------
    tth : ndarray
        X-axis values (2theta or Q)
    intensity : ndarray
        Integrated intensity values
    """
    try:
        # Perform 1D integration
        # This matches Dioptas integration approach
        result = ai.integrate1d(
            image,
            npt=num_points,
            unit=unit,
            correctSolidAngle=True,
            polarization_factor=0.95,  # Typical for synchrotron
            method="splitpixel"
        )
        
        tth = result[0]
        intensity = result[1]
        
        # Convert to degrees if needed
        if unit == "2th_deg" and tth[0] < 1:
            tth = np.degrees(tth)
        
        return tth, intensity
    except Exception as e:
        print(f"Error creating pattern: {e}")
        return None, None


def plot_cake_with_rings(axes, cake, tth_array, chi_array, calibrant=None, wavelength=None):
    """
    Plot cake image with calibrant ring overlays
    Based on Dioptas cake display
    
    Parameters:
    -----------
    axes : matplotlib axes
        Axes to plot on
    cake : ndarray
        Cake image data
    tth_array : ndarray
        2theta values
    chi_array : ndarray
        Chi values
    calibrant : Calibrant (optional)
        Calibrant object to overlay ring positions
    wavelength : float (optional)
        X-ray wavelength in meters
    """
    axes.clear()
    
    # Plot cake image with log scale for better visibility
    extent = [tth_array[0], tth_array[-1], chi_array[0], chi_array[-1]]
    
    # Use log scale for intensity
    cake_display = np.log10(cake + 1)
    
    im = axes.imshow(
        cake_display,
        aspect='auto',
        extent=extent,
        origin='lower',
        cmap='viridis',
        interpolation='nearest'
    )
    
    # Overlay calibrant rings if available
    if calibrant is not None and wavelength is not None:
        try:
            # Get expected ring positions
            tth_calibrant = calibrant.get_2th()
            tth_deg = np.degrees(tth_calibrant)
            
            # Draw vertical lines for each ring
            for i, tth in enumerate(tth_deg[:10]):  # Show first 10 rings
                if tth_array[0] <= tth <= tth_array[-1]:
                    axes.axvline(tth, color='red', linestyle='--', 
                               linewidth=0.5, alpha=0.6)
                    # Label ring number
                    axes.text(tth, chi_array[-1] * 0.95, f'{i+1}', 
                            color='red', fontsize=8, ha='center')
        except Exception as e:
            print(f"Error plotting calibrant rings: {e}")
    
    axes.set_xlabel('2θ (degrees)', fontsize=10)
    axes.set_ylabel('Azimuthal angle χ (degrees)', fontsize=10)
    axes.set_title('Cake View (Polar Transform)', fontsize=11, fontweight='bold')
    
    return im


def plot_pattern_with_peaks(axes, tth, intensity, calibrant=None, wavelength=None):
    """
    Plot 1D pattern with calibrant peak overlays
    Based on Dioptas pattern display
    
    Parameters:
    -----------
    axes : matplotlib axes
        Axes to plot on
    tth : ndarray
        2theta or Q values
    intensity : ndarray
        Intensity values
    calibrant : Calibrant (optional)
        Calibrant object to overlay peak positions
    wavelength : float (optional)
        X-ray wavelength in meters
    """
    axes.clear()
    
    # Plot integrated pattern
    axes.plot(tth, intensity, 'b-', linewidth=1.0, label='Integrated Pattern')
    
    # Overlay calibrant peak positions if available
    if calibrant is not None and wavelength is not None:
        try:
            # Get expected peak positions
            tth_calibrant = calibrant.get_2th()
            tth_deg = np.degrees(tth_calibrant)
            
            # Find y-position for markers (90% of max intensity)
            y_max = np.max(intensity)
            y_pos = y_max * 0.9
            
            # Draw vertical lines and labels for each expected peak
            for i, tth_peak in enumerate(tth_deg[:15]):  # Show first 15 peaks
                if tth[0] <= tth_peak <= tth[-1]:
                    axes.axvline(tth_peak, color='red', linestyle='--', 
                               linewidth=0.8, alpha=0.5)
                    # Label ring number
                    axes.text(tth_peak, y_pos, f'{i+1}', 
                            color='red', fontsize=7, ha='center', 
                            rotation=90, va='bottom')
        except Exception as e:
            print(f"Error plotting calibrant peaks: {e}")
    
    axes.set_xlabel('2θ (degrees)', fontsize=10)
    axes.set_ylabel('Intensity (a.u.)', fontsize=10)
    axes.set_title('Integrated Diffraction Pattern', fontsize=11, fontweight='bold')
    axes.grid(True, alpha=0.3, linestyle='--')
    axes.set_xlim(tth[0], tth[-1])
    
    # Use log scale for y-axis if data spans many orders of magnitude
    if np.max(intensity) / (np.min(intensity[intensity > 0]) + 1e-10) > 100:
        axes.set_yscale('log')
    
    axes.legend(loc='upper right', fontsize=9)


def export_cake_image(cake, tth_array, chi_array, filename):
    """Export cake image to file"""
    try:
        fig, ax = plt.subplots(figsize=(10, 8))
        plot_cake_with_rings(ax, cake, tth_array, chi_array)
        fig.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error exporting cake image: {e}")
        return False


def export_pattern_data(tth, intensity, filename):
    """Export pattern data to text file"""
    try:
        header = "2theta(deg)\tIntensity(a.u.)"
        data = np.column_stack((tth, intensity))
        np.savetxt(filename, data, delimiter='\t', header=header, comments='')
        return True
    except Exception as e:
        print(f"Error exporting pattern data: {e}")
        return False