!===============================================================================
! CFML_EoS_Core - Simplified CrysFML EoS Core for Python Integration
!===============================================================================
! Based on CrysFML CFML_EoS.f90 by J. Rodriguez-Carvajal, J. Gonzalez-Platas, R.J. Angel
! Simplified version with minimal dependencies for f2py compilation
!
! This module implements the core EoS calculations from CrysFML:
! - Birch-Murnaghan 2nd/3rd/4th order
! - Murnaghan
! - Vinet
! - Natural Strain
!
! Reference: Angel, R.J., et al. (2014) Z. Kristallogr. 229, 405-419
!===============================================================================

module cfml_eos_core
    implicit none
    
    ! Precision
    integer, parameter :: dp = kind(1.0d0)
    real(dp), parameter :: PI = 3.141592653589793_dp
    
    ! EoS model types
    integer, parameter :: MURNAGHAN = 1
    integer, parameter :: BM2 = 2
    integer, parameter :: BM3 = 3
    integer, parameter :: BM4 = 4
    integer, parameter :: VINET = 5
    integer, parameter :: NATURAL_STRAIN = 6
    
contains

    !---------------------------------------------------------------------------
    ! CFML_EoS Core Calculation Routines
    !---------------------------------------------------------------------------
    
    !> Birch-Murnaghan 3rd order P(V) - Core CrysFML Algorithm
    pure function bm3_pressure_cfml(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p, f, x, prefactor, correction
        
        ! CFML Method: Using Eulerian strain formulation
        ! This matches CFML_EoS.f90 implementation
        x = (v0/v)**(1.0_dp/3.0_dp)
        f = 0.5_dp * (x*x - 1.0_dp)
        
        ! P = 3*K0*f*(1+2f)^(5/2) * [1 + 3/2*(K'-4)*f]
        prefactor = 3.0_dp * k0 * f * (1.0_dp + 2.0_dp*f)**2.5_dp
        correction = 1.0_dp + 1.5_dp * (kp - 4.0_dp) * f
        
        p = prefactor * correction
    end function bm3_pressure_cfml
    
    !> Birch-Murnaghan 2nd order P(V)
    pure function bm2_pressure_cfml(v, v0, k0) result(p)
        real(dp), intent(in) :: v, v0, k0
        real(dp) :: p, f, x
        
        x = (v0/v)**(1.0_dp/3.0_dp)
        f = 0.5_dp * (x*x - 1.0_dp)
        
        p = 3.0_dp * k0 * f * (1.0_dp + 2.0_dp*f)**2.5_dp
    end function bm2_pressure_cfml
    
    !> Birch-Murnaghan 4th order P(V)
    pure function bm4_pressure_cfml(v, v0, k0, kp, kpp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp, kpp
        real(dp) :: p, f, x, h
        
        x = (v0/v)**(1.0_dp/3.0_dp)
        f = 0.5_dp * (x*x - 1.0_dp)
        
        h = 1.0_dp + (3.0_dp/2.0_dp)*(kp - 4.0_dp)*f + &
            (3.0_dp/2.0_dp)*f*f*(k0*kpp + (kp-4.0_dp)*(kp-3.0_dp) + 35.0_dp/9.0_dp)
        
        p = 3.0_dp * k0 * f * (1.0_dp + 2.0_dp*f)**2.5_dp * h
    end function bm4_pressure_cfml
    
    !> Murnaghan P(V)
    pure function murnaghan_pressure_cfml(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p
        
        p = (k0/kp) * ((v0/v)**kp - 1.0_dp)
    end function murnaghan_pressure_cfml
    
    !> Vinet P(V)
    pure function vinet_pressure_cfml(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p, eta
        
        eta = (v/v0)**(1.0_dp/3.0_dp)
        p = 3.0_dp * k0 * (1.0_dp - eta) / eta**2 * &
            exp(1.5_dp * (kp - 1.0_dp) * (1.0_dp - eta))
    end function vinet_pressure_cfml
    
    !> Natural Strain P(V)
    pure function natural_strain_pressure_cfml(v, v0, k0, kp) result(p)
        real(dp), intent(in) :: v, v0, k0, kp
        real(dp) :: p, fn
        
        fn = log(v/v0)
        p = -k0 * fn * (1.0_dp - 0.5_dp * (kp - 2.0_dp) * fn)
    end function natural_strain_pressure_cfml
    
    !> Universal pressure calculator - CrysFML style
    pure function calc_pressure_cfml(v, v0, k0, kp, kpp, imodel) result(p)
        real(dp), intent(in) :: v, v0, k0, kp, kpp
        integer, intent(in) :: imodel
        real(dp) :: p
        
        select case(imodel)
            case(MURNAGHAN)
                p = murnaghan_pressure_cfml(v, v0, k0, kp)
            case(BM2)
                p = bm2_pressure_cfml(v, v0, k0)
            case(BM3)
                p = bm3_pressure_cfml(v, v0, k0, kp)
            case(BM4)
                p = bm4_pressure_cfml(v, v0, k0, kp, kpp)
            case(VINET)
                p = vinet_pressure_cfml(v, v0, k0, kp)
            case(NATURAL_STRAIN)
                p = natural_strain_pressure_cfml(v, v0, k0, kp)
            case default
                p = bm3_pressure_cfml(v, v0, k0, kp)
        end select
    end function calc_pressure_cfml
    
    !> Vectorized pressure calculation
    subroutine calc_pressure_array_cfml(v_arr, n, v0, k0, kp, kpp, imodel, p_arr)
        integer, intent(in) :: n, imodel
        real(dp), dimension(n), intent(in) :: v_arr
        real(dp), intent(in) :: v0, k0, kp, kpp
        real(dp), dimension(n), intent(out) :: p_arr
        integer :: i
        
        do i = 1, n
            p_arr(i) = calc_pressure_cfml(v_arr(i), v0, k0, kp, kpp, imodel)
        end do
    end subroutine calc_pressure_array_cfml
    
    !---------------------------------------------------------------------------
    ! CFML_EoS F-f Linearization Method for BM3 Fitting
    !---------------------------------------------------------------------------
    
    !> CFML Key Method: F-f transformation for stable BM3 fitting
    !  This is the core innovation from Angel et al. (2014)
    !  Transforms P-V data to linearized form for stable K' determination
    subroutine ff_transform_cfml(v_arr, p_arr, n, v0, f_arr, F_arr)
        integer, intent(in) :: n
        real(dp), dimension(n), intent(in) :: v_arr, p_arr
        real(dp), intent(in) :: v0
        real(dp), dimension(n), intent(out) :: f_arr, F_arr
        integer :: i
        real(dp) :: x, f, denom
        
        do i = 1, n
            ! Eulerian strain: f = [(V0/V)^(2/3) - 1] / 2
            x = (v0/v_arr(i))**(1.0_dp/3.0_dp)
            f = 0.5_dp * (x*x - 1.0_dp)
            f_arr(i) = f
            
            ! Normalized stress: F = P / [3f(1+2f)^(5/2)]
            if (abs(f) > 1.0d-10) then
                denom = 3.0_dp * f * (1.0_dp + 2.0_dp*f)**2.5_dp
                F_arr(i) = p_arr(i) / denom
            else
                ! Limit for small strain
                F_arr(i) = p_arr(i) / (3.0_dp * v0)
            end if
        end do
    end subroutine ff_transform_cfml
    
    !> CFML Fitting Method: BM3 using F-f linearization with Tikhonov regularization
    subroutine fit_bm3_cfml(v_arr, p_arr, n, v0_out, k0_out, kp_out, chi2_out, converged)
        integer, intent(in) :: n
        real(dp), dimension(n), intent(in) :: v_arr, p_arr
        real(dp), intent(out) :: v0_out, k0_out, kp_out, chi2_out
        logical, intent(out) :: converged
        
        ! Local variables
        real(dp), dimension(n) :: f_arr, F_arr, weights, p_calc, residuals
        real(dp) :: v0_current, v0_prev
        real(dp) :: sum_w, sum_wf, sum_wf2, sum_wF, sum_wfF
        real(dp) :: b0, b1, denom, lambda_reg, v0_change
        integer :: iter, i
        integer, parameter :: max_iter = 20
        real(dp), parameter :: tol = 1.0d-6
        real(dp), parameter :: reg_strength = 1.0_dp
        
        converged = .false.
        
        ! Initial V0 guess
        v0_current = maxval(v_arr) * 1.02_dp
        
        ! Iterative V0 refinement using CFML F-f method
        do iter = 1, max_iter
            v0_prev = v0_current
            
            ! F-f transformation
            call ff_transform_cfml(v_arr, p_arr, n, v0_current, f_arr, F_arr)
            
            ! CFML weighting: emphasize low-strain data
            do i = 1, n
                weights(i) = 1.0_dp / (f_arr(i)**2 + 0.001_dp)
            end do
            
            ! Normalize weights
            sum_w = sum(weights)
            weights = weights * real(n, dp) / sum_w
            
            ! Weighted linear regression: F = b0 + b1*f
            ! With Tikhonov regularization on b1 (K' constraint)
            sum_wf = sum(weights * f_arr)
            sum_wf2 = sum(weights * f_arr * f_arr)
            sum_wF = sum(weights * F_arr)
            sum_wfF = sum(weights * f_arr * F_arr)
            
            ! Regularization parameter
            lambda_reg = reg_strength * sum_w / real(n, dp)
            
            ! Regularized normal equations
            denom = sum_w * sum_wf2 - sum_wf**2 + lambda_reg * sum_w
            
            if (abs(denom) > 1.0d-10) then
                b1 = (sum_w * sum_wfF - sum_wf * sum_wF) / denom
                b0 = (sum_wF - b1 * sum_wf) / sum_w
                
                k0_out = b0
                kp_out = 4.0_dp + b1
                
                ! Physical constraints
                if (k0_out < 20.0_dp .or. k0_out > 800.0_dp) exit
                if (kp_out < 2.0_dp .or. kp_out > 8.0_dp) exit
                
                ! Update V0 (simple damped step)
                v0_current = v0_current * 1.005_dp
                
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
        
        v0_out = v0_current
        
        ! Calculate final chi-square
        do i = 1, n
            p_calc(i) = bm3_pressure_cfml(v_arr(i), v0_out, k0_out, kp_out)
            residuals(i) = p_arr(i) - p_calc(i)
        end do
        
        chi2_out = sum(weights * residuals**2) / real(n - 2, dp)
        
    end subroutine fit_bm3_cfml
    
end module cfml_eos_core
