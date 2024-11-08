from os import path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

import gymnasium as gym
from gymnasium import error, spaces
from gymnasium.spaces import Space

import asyncio
import sys
from orca_gym import OrcaGymRemote, OrcaGymLocal
from orca_gym.protos.mjc_message_pb2_grpc import GrpcServiceStub 
from orca_gym.utils.rotations import mat2quat, quat2mat

from orca_gym import OrcaGymModel
from orca_gym import OrcaGymData
from envs import OrcaGymBaseEnv, RewardType

import grpc

import mujoco
from datetime import datetime
import time

class OrcaGymLocalEnv(OrcaGymBaseEnv):
    def __init__(
        self,
        frame_skip: int,
        grpc_address: str,
        agent_names: list[str],
        time_step: float,        
        **kwargs        
    ):
        super().__init__(
            frame_skip = frame_skip,
            grpc_address = grpc_address,
            agent_names = agent_names,
            time_step = time_step,            
            **kwargs
        )

        render_fps = 30
        self._render_interval = 1.0 / render_fps
        self._render_time_step = time.perf_counter()


    def initialize_simulation(
        self,
    ) -> Tuple[OrcaGymModel, OrcaGymData]:
        print(f"Initializing simulation: Class: {self.__class__.__name__}")
        self.loop.run_until_complete(self._initialize_orca_sim())
        model = self.gym.model
        data = self.gym.data
        return model, data

    async def _initialize_orca_sim(self):
        await self.gym.init_simulation()
        return

    def initialize_grpc(self):
        self.channel = grpc.aio.insecure_channel(self.grpc_address)
        self.stub = GrpcServiceStub(self.channel)
        self.gym = OrcaGymLocal(self.stub)

    def pause_simulation(self):
        self.loop.run_until_complete(self._pause_simulation())

    async def _pause_simulation(self):
        await self.gym.pause_simulation()

    def do_simulation(self, ctrl, n_frames) -> None:
        """
        Step the simulation n number of frames and applying a control action.
        """
        # Check control input is contained in the action space
        if np.array(ctrl).shape != (self.model.nu,):
            raise ValueError(
                f"Action dimension mismatch. Expected {(self.model.nu,)}, found {np.array(ctrl).shape}"
            )
        self._step_orca_sim_simulation(ctrl, n_frames)
        self.gym.update_data()


    @property
    def render_mode(self) -> str:
        if hasattr(self, "_render_mode"):
            return self._render_mode
        else:
            return "human"

    def render(self):
        time_diff = time.perf_counter() - self._render_time_step
        if (time_diff > self._render_interval):
            self._render_time_step = time.perf_counter()
            if self.render_mode == "human":
                self.loop.run_until_complete(self.gym.render())
            

    def set_ctrl(self, ctrl):
        self.gym.set_ctrl(ctrl)

    def mj_step(self, nstep):
        self.gym.mj_step(nstep)

    def _step_orca_sim_simulation(self, ctrl, n_frames):
        self.set_ctrl(ctrl)
        self.mj_step(nstep=n_frames)

    def set_time_step(self, time_step):
        self.gym.set_time_step(time_step)
        return

    def reset_simulation(self):
        self.gym.load_initial_frame()
        self.gym.update_data()

    def init_qpos_qvel(self):
        self.gym.update_data()
        self.init_qpos = self.gym.data.qpos.ravel().copy()
        self.init_qvel = self.gym.data.qvel.ravel().copy()

    def query_joint_offsets(self, joint_names) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        qpos_offsets, qvel_offsets, qacc_offsets = self.gym.query_joint_offsets(joint_names)
        return qpos_offsets, qvel_offsets, qacc_offsets
    
    
    def get_body_xpos_xmat_xquat(self, body_name_list):
        body_dict = self.gym.query_body_xpos_xmat_xquat(body_name_list)
        if len(body_dict) != len(body_name_list):
            print("Body Nmae List: ", body_name_list)
            print("Body Dict: ", body_dict)
            raise ValueError("Some body names are not found in the simulation.")
        xpos = np.array([body_dict[body_name]['Pos'] for body_name in body_name_list]).flat.copy()
        xmat = np.array([body_dict[body_name]['Mat'] for body_name in body_name_list]).flat.copy()
        xquat = np.array([body_dict[body_name]['Quat'] for body_name in body_name_list]).flat.copy()
        return xpos, xmat, xquat
    
    def query_sensor_data(self, sensor_names):
        sensor_data_dict = self.gym.query_sensor_data(sensor_names)
        return sensor_data_dict
    
    def query_joint_qpos(self, joint_names):
        joint_qpos_dict = self.gym.query_joint_qpos(joint_names)
        return joint_qpos_dict
    
    def query_joint_qvel(self, joint_names):
        joint_qvel_dict = self.gym.query_joint_qvel(joint_names)
        return joint_qvel_dict
    
    def jnt_qposadr(self, joint_name):
        joint_qposadr = self.gym.jnt_qposadr(joint_name)
        return joint_qposadr
    
    def jnt_dofadr(self, joint_name):
        joint_dofadr = self.gym.jnt_dofadr(joint_name)
        return joint_dofadr