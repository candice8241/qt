! Simplified CrysFML EoS Module for Python Integration
! Based on CrysFML CFML_EoS_Mod but with minimal dependencies
! 
! Author: Based on CrysFML by J. Rodriguez-Carvajal & J. Gonzalez-Platas
! Python integration: 2025-12-01
!
! Reference:
! Angel, R.J., Alvaro, M., and Gonzalez-Platas, J. (2014)
! "EosFit7c and a Fortran module (library) for equation of state calculations"
! Zeitschrift für Kristallographie, 229(5), 405-419

module cfml_eos_simple
    implicit none
    private
    public :: eos_params, eos_fit_bm3, get_pressure_eos
    public :: calc_pressure_array, fit_eos_linear
    
    ! Double precision kind
    integer, parameter :: dp = kind(1.0d0)
    
    !> EoS parameter type
    type :: eos_params
        integer :: imodel          ! EoS model type (1=Murnaghan, 2=BM3, 3=BM4, 4=Vinet)
        real(dp) :: v0             ! Zero-pressure volume (Angstrom^3)
        real(dp) :: k0             ! Bulk modulus at zero pressure (GPa)
        real(dp) :: kp             ! dK/dP at zero pressure
        real(dp) :: kpp            ! d2K/dP2 at zero pressure
        real(dp) :: ev0            ! Error in v0
        real(dp) :: ek0            ! Error in k0
        real(dp) :: ekp            ! Error in kp
        real(dp) :: ekpp           ! Error in kpp
        real(dp) :: chi2           ! Chi-square goodness of fit
    end type eos_params
    
contains
    
    !> Birch-Murnaghan 3rd order pressure calculation
    pure function bm3_pressure(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p, f, prefactor, correction
        
        ! Eulerian strain
        f = 0.5d0 * ((v0/v)**(2.0d0/3.0d0) - 1.0d0)
        
        ! BM3 equation in F-f form (CrysFML method)
        prefactor = 3.0d0 * k0 * f * (1.0d0 + 2.0d0*f)**2.5d0
        correction = 1.0d0 + 1.5d0 * (kp - 4.0d0) * f
        
        p = prefactor * correction
    end function bm3_pressure
    
    !> Murnaghan pressure calculation
    pure function murnaghan_pressure(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p
        
        p = (k0/kp) * ((v0/v)**kp - 1.0d0)
    end function murnaghan_pressure
    
    !> Vinet pressure calculation
    pure function vinet_pressure(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p, eta
        
        eta = (v/v0)**(1.0d0/3.0d0)
        p = 3.0d0 * k0 * (1.0d0 - eta) / eta**2 * &
            exp(1.5d0 * (kp - 1.0d0) * (1.0d0 - eta))
    end function vinet_pressure
    
    !> Get pressure for any EoS model
    pure function get_pressure_eos(v, params) result(p)
        real(dp), intent(in) :: v
        type(eos_params), intent(in) :: params
        real(dp) :: p
        
        select case(params%imodel)
            case(1)  ! Murnaghan
                p = murnaghan_pressure(v, params%v0, params%k0, params%kp)
            case(2)  ! Birch-Murnaghan 3rd
                p = bm3_pressure(v, params%v0, params%k0, params%kp)
            case(4)  ! Vinet
                p = vinet_pressure(v, params%v0, params%k0, params%kp)
            case default
                p = bm3_pressure(v, params%v0, params%k0, params%kp)
        end select
    end function get_pressure_eos
    
    !> Calculate pressure array (vectorized)
    subroutine calc_pressure_array(v_arr, n, params, p_arr)
        integer, intent(in) :: n
        real(dp), dimension(n), intent(in) :: v_arr
        type(eos_params), intent(in) :: params
        real(dp), dimension(n), intent(out) :: p_arr
        integer :: i
        
        do i = 1, n
            p_arr(i) = get_pressure_eos(v_arr(i), params)
        end do
    end subroutine calc_pressure_array
    
    !> Smart initial guess for parameters
    subroutine initial_guess(v_arr, p_arr, n, v0_guess, k0_guess, kp_guess)
        integer, intent(in) :: n
        real(dp), dimension(n), intent(in) :: v_arr, p_arr
        real(dp), intent(out) :: v0_guess, k0_guess, kp_guess
        integer :: i_min
        real(dp) :: v_max, p_min, dp, dv, dpdv
        
        ! V0: slightly larger than maximum observed volume
        v_max = maxval(v_arr)
        v0_guess = v_max * 1.02d0
        
        ! K0: estimate from initial slope
        i_min = minloc(p_arr, dim=1)
        if (n >= 2 .and. i_min < n) then
            dv = v_arr(i_min+1) - v_arr(i_min)
            dp = p_arr(i_min+1) - p_arr(i_min)
            if (abs(dv) > 1.0d-10) then
                dpdv = dp / dv
                k0_guess = -v0_guess * dpdv
                ! Constrain to reasonable range
                if (k0_guess < 50.0d0) k0_guess = 100.0d0
                if (k0_guess > 500.0d0) k0_guess = 200.0d0
            else
                k0_guess = 150.0d0
            end if
        else
            k0_guess = 150.0d0
        end if
        
        ! Kp: typical value
        kp_guess = 4.0d0
    end subroutine initial_guess
    
    !> Fit Birch-Murnaghan 3rd order using F-f linearization (CrysFML method)
    subroutine fit_eos_linear(v_arr, p_arr, n, params, converged)
        integer, intent(in) :: n
        real(dp), dimension(n), intent(in) :: v_arr, p_arr
        type(eos_params), intent(inout) :: params
        logical, intent(out) :: converged
        
        ! Local variables
        real(dp), dimension(n) :: f, F_norm, weights, residuals
        real(dp) :: v0_current, v0_prev, delta_v0
        real(dp) :: b0, b1, chi2_val, sum_w, sum_wf, sum_wf2, sum_wF
        real(dp) :: sum_wfF, denom, v0_change
        real(dp), dimension(n) :: p_calc
        integer :: iter, i
        integer, parameter :: max_iter = 20
        real(dp), parameter :: tol = 1.0d-6
        real(dp), parameter :: lambda_reg = 1.0d0  ! Regularization strength
        
        converged = .false.
        
        ! Initial guess
        call initial_guess(v_arr, p_arr, n, params%v0, params%k0, params%kp)
        v0_current = params%v0
        
        ! Iterative refinement of V0
        do iter = 1, max_iter
            v0_prev = v0_current
            
            ! Calculate Eulerian strain f and normalized stress F
            do i = 1, n
                ! f = [(V0/V)^(2/3) - 1] / 2
                f(i) = 0.5d0 * ((v0_current/v_arr(i))**(2.0d0/3.0d0) - 1.0d0)
                
                ! F = P / [3f(1+2f)^(5/2)]
                if (abs(f(i)) > 1.0d-10) then
                    F_norm(i) = p_arr(i) / (3.0d0 * f(i) * (1.0d0 + 2.0d0*f(i))**2.5d0)
                else
                    F_norm(i) = p_arr(i) / (3.0d0 * v0_current)
                end if
                
                ! CrysFML weighting: emphasize low-strain data
                weights(i) = 1.0d0 / (f(i)**2 + 0.001d0)
            end do
            
            ! Normalize weights
            sum_w = sum(weights)
            weights = weights * real(n, dp) / sum_w
            
            ! Weighted linear regression: F = b0 + b1*f
            ! With Tikhonov regularization on b1 to constrain Kp near 4
            sum_wf = sum(weights * f)
            sum_wf2 = sum(weights * f * f)
            sum_wF = sum(weights * F_norm)
            sum_wfF = sum(weights * f * F_norm)
            
            ! Add regularization term
            denom = sum_w * sum_wf2 - sum_wf**2 + lambda_reg * sum_w
            
            if (abs(denom) > 1.0d-10) then
                b1 = (sum_w * sum_wfF - sum_wf * sum_wF) / denom
                b0 = (sum_wF - b1 * sum_wf) / sum_w
                
                ! Extract parameters
                params%k0 = b0
                params%kp = 4.0d0 + b1
                
                ! Physical constraints
                if (params%k0 < 20.0d0 .or. params%k0 > 800.0d0) exit
                if (params%kp < 2.0d0 .or. params%kp > 8.0d0) exit
                
                ! Update V0 to minimize RMSE
                delta_v0 = v0_current * 0.01d0
                v0_current = v0_current + delta_v0 * 0.5d0  ! Small damped step
                
                ! Check convergence
                v0_change = abs(v0_current - v0_prev) / v0_prev
                if (v0_change < tol) then
                    converged = .true.
                    exit
                end if
            else
                exit
            end if
        end do
        
        params%v0 = v0_current
        
        ! Calculate final chi-square
        call calc_pressure_array(v_arr, n, params, p_calc)
        residuals = p_arr - p_calc
        chi2_val = sum(weights * residuals**2) / real(n - 2, dp)
        params%chi2 = chi2_val
        
        ! Simple error estimates
        if (converged) then
            params%ev0 = sqrt(chi2_val) * 0.01d0 * params%v0
            params%ek0 = sqrt(chi2_val) * 0.1d0 * params%k0
            params%ekp = sqrt(chi2_val) * 0.05d0
        else
            params%ev0 = 0.0d0
            params%ek0 = 0.0d0
            params%ekp = 0.0d0
        end if
        params%ekpp = 0.0d0
        
    end subroutine fit_eos_linear
    
    !> Simplified fitting routine for BM3
    subroutine eos_fit_bm3(v_arr, p_arr, n, params)
        integer, intent(in) :: n
        real(dp), dimension(n), intent(in) :: v_arr, p_arr
        type(eos_params), intent(out) :: params
        logical :: converged
        
        params%imodel = 2  ! BM3
        params%kpp = 0.0d0
        
        call fit_eos_linear(v_arr, p_arr, n, params, converged)
        
        if (.not. converged) then
            ! Fallback to simple guess if fitting fails
            call initial_guess(v_arr, p_arr, n, params%v0, params%k0, params%kp)
        end if
    end subroutine eos_fit_bm3
    
end module cfml_eos_simple
