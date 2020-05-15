#!/usr/bin/env python3
import sys

import numpy as np
import sympy as sp

from rednose.helpers.ekf_sym import EKF_sym, gen_code

EARTH_GM = 3.986005e14  # m^3/s^2 (gravitational constant * mass of earth)


class ObservationKind():
  UNKNOWN = 0
  NO_OBSERVATION = 1
  POSITION = 1

  names = [
    'Unknown',
    'No observation',
    'Position'
  ]

  @classmethod
  def to_string(cls, kind):
    return cls.names[kind]


class States():
  POSITION = slice(0, 1)
  VELOCITY = slice(1, 2)


class KinematicKalman():
  name = 'kinematic'

  initial_x = np.array([0.5, 0.0])

  # state covariance
  initial_P_diag = np.array([1.0**2, 1.0**2])

  # process noise
  Q = np.diag([0.1**2, 2.0**2])

  @staticmethod
  def generate_code(generated_dir):
    name = KinematicKalman.name
    dim_state = KinematicKalman.initial_x.shape[0]

    state_sym = sp.MatrixSymbol('state', dim_state, 1)
    state = sp.Matrix(state_sym)

    position = state[States.POSITION, :][0,:]
    velocity = state[States.VELOCITY, :][0,:]

    dt = sp.Symbol('dt')
    state_dot = sp.Matrix(np.zeros((dim_state, 1)))
    state_dot[States.POSITION.start, 0] = velocity
    f_sym = state + dt * state_dot

    obs_eqs = [
      [sp.Matrix([position]), ObservationKind.POSITION, None],
    ]

    gen_code(generated_dir, name, f_sym, dt, state_sym, obs_eqs, dim_state, dim_state)

  def __init__(self, generated_dir):
    self.dim_state = self.initial_x.shape[0]
    self.dim_state_err = self.initial_P_diag.shape[0]

    self.obs_noise = {ObservationKind.POSITION: np.atleast_2d(0.1**2)}

    # init filter
    self.filter = EKF_sym(generated_dir, self.name, self.Q, self.initial_x, np.diag(self.initial_P_diag), self.dim_state, self.dim_state_err)

  @property
  def x(self):
    return self.filter.state()

  @property
  def t(self):
    return self.filter.filter_time

  @property
  def P(self):
    return self.filter.covs()

  def init_state(self, state, covs_diag=None, covs=None, filter_time=None):
    if covs_diag is not None:
      P = np.diag(covs_diag)
    elif covs is not None:
      P = covs
    else:
      P = self.filter.covs()
    self.filter.init_state(state, P, filter_time)

  def get_R(self, kind, n):
    obs_noise = self.obs_noise[kind]
    dim = obs_noise.shape[0]
    R = np.zeros((n, dim, dim))
    for i in range(n):
      R[i, :, :] = obs_noise
    return R

  def predict_and_observe(self, t, kind, data, R=None):
    if len(data) > 0:
      data = np.atleast_2d(data)

    if R is None:
      R = self.get_R(kind, len(data))

    self.filter.predict_and_update_batch(t, kind, data, R)


if __name__ == "__main__":
  generated_dir = sys.argv[2]
  KinematicKalman.generate_code(generated_dir)
