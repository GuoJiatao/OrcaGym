import numpy as np
from gymnasium.core import ObsType
from envs.robot_env import MujocoRobotEnv
from orca_gym.utils import rotations
from typing import Optional, Any, SupportsFloat
from gymnasium import spaces
from orca_gym.devices.xbox_joystick import XboxJoystickManager
from orca_gym.devices.pico_joytsick import PicoJoystick
from orca_gym.robosuite.controllers.controller_factory import controller_factory
import orca_gym.robosuite.controllers.controller_config as controller_config
import orca_gym.robosuite.utils.transform_utils as transform_utils
import h5py
from scipy.spatial.transform import Rotation as R

class RecordState:
    RECORD = "record"
    REPLAY = "replay"
    REPLAY_FINISHED = "replay_finished"
    NONE = "none"

class OpenloongArmEnv(MujocoRobotEnv):
    """
    控制青龙机器人机械臂
    """
    def __init__(
        self,
        frame_skip: int = 5,        
        grpc_address: str = 'localhost:50051',
        agent_names: list = ['Agent0'],
        time_step: float = 0.00333333,
        record_state: str = RecordState.NONE,        
        record_file: Optional[str] = None,
        control_freq: int = 20,
        **kwargs,
    ):

        self.record_state = record_state
        self.record_file = record_file
        self.record_pool = []
        self.RECORD_POOL_SIZE = 1000
        self.record_cursor = 0

        action_size = 3 # 实际并不使用

        self.control_freq = control_freq

        super().__init__(
            frame_skip = frame_skip,
            grpc_address = grpc_address,
            agent_names = agent_names,
            time_step = time_step,            
            n_actions=action_size,
            observation_space = None,
            **kwargs,
        )


        # Three auxiliary variables to understand the component of the xml document but will not be used
        # number of actuators/controls: 7 arm joints and 2 gripper joints
        self.nu = self.model.nu
        # 16 generalized coordinates: 9 (arm + gripper) + 7 (object free joint: 3 position and 4 quaternion coordinates)
        self.nq = self.model.nq
        # 9 arm joints and 6 free joints
        self.nv = self.model.nv

        self._base_body_name = [self.body("base_link")]
        self._base_body_xpos, _, self._base_body_xquat = self.get_body_xpos_xmat_xquat(self._base_body_name)
        print("base_body_xpos: ", self._base_body_xpos)
        print("base_body_xquat: ", self._base_body_xquat)

        # index used to distinguish arm and gripper joints
        self._r_arm_joint_names = [self.joint("J_arm_r_01"), self.joint("J_arm_r_02"), 
                                 self.joint("J_arm_r_03"), self.joint("J_arm_r_04"), 
                                 self.joint("J_arm_r_05"), self.joint("J_arm_r_06"), self.joint("J_arm_r_07")]
        self._r_arm_moto_names = [self.actuator("M_arm_r_01"), self.actuator("M_arm_r_02"),
                                self.actuator("M_arm_r_03"),self.actuator("M_arm_r_04"),
                                self.actuator("M_arm_r_05"),self.actuator("M_arm_r_06"),self.actuator("M_arm_r_07")]
        self._r_arm_actuator_id = [self.model.actuator_name2id(actuator_name) for actuator_name in self._r_arm_moto_names]
        self._r_neutral_joint_values = np.array([0.905, -0.735, -2.733, 1.405, -1.191, 0.012, -0.517])
        
        self._r_hand_moto_names = [self.actuator("M_zbr_J1"), self.actuator("M_zbr_J2"), self.actuator("M_zbr_J3")
                                   ,self.actuator("M_zbr_J4"),self.actuator("M_zbr_J5"),self.actuator("M_zbr_J6"),
                                   self.actuator("M_zbr_J7"),self.actuator("M_zbr_J8"),self.actuator("M_zbr_J9"),
                                   self.actuator("M_zbr_J10"),self.actuator("M_zbr_J11")]
        self._r_hand_actuator_id = [self.model.actuator_name2id(actuator_name) for actuator_name in self._r_hand_moto_names]

        print("arm_actuator_id: ", self._r_arm_actuator_id)
        print("hand_actuator_id: ", self._r_hand_actuator_id)

        # index used to distinguish arm and gripper joints
        self._l_arm_joint_names = [self.joint("J_arm_l_01"), self.joint("J_arm_l_02"), 
                                 self.joint("J_arm_l_03"), self.joint("J_arm_l_04"), 
                                 self.joint("J_arm_l_05"), self.joint("J_arm_l_06"), self.joint("J_arm_l_07")]
        self._l_arm_moto_names = [self.actuator("M_arm_l_01"), self.actuator("M_arm_l_02"),
                                self.actuator("M_arm_l_03"),self.actuator("M_arm_l_04"),
                                self.actuator("M_arm_l_05"),self.actuator("M_arm_l_06"),self.actuator("M_arm_l_07")]
        self._l_arm_actuator_id = [self.model.actuator_name2id(actuator_name) for actuator_name in self._l_arm_moto_names]
        self._l_neutral_joint_values = np.array([-0.905, 0.735, 2.733, 1.405, 1.191, 0.012, 0.517])
        # self._l_neutral_joint_values = np.zeros(7)

        print("arm_actuator_id: ", self._l_arm_actuator_id)
        self._l_hand_moto_names = [self.actuator("M_zbll_J1"), self.actuator("M_zbll_J2"), self.actuator("M_zbll_J3")
                                    ,self.actuator("M_zbll_J4"),self.actuator("M_zbll_J5"),self.actuator("M_zbll_J6"),
                                    self.actuator("M_zbll_J7"),self.actuator("M_zbll_J8"),self.actuator("M_zbll_J9"),
                                    self.actuator("M_zbll_J10"),self.actuator("M_zbll_J11")]
        self._l_hand_actuator_id = [self.model.actuator_name2id(actuator_name) for actuator_name in self._l_hand_moto_names]        

        # control range
        self._all_ctrlrange = self.model.get_actuator_ctrlrange()
        r_ctrl_range = [self._all_ctrlrange[actoator_id] for actoator_id in self._r_arm_actuator_id]
        print("ctrl_range: ", r_ctrl_range)

        l_ctrl_range = [self._all_ctrlrange[actoator_id] for actoator_id in self._l_arm_actuator_id]
        print("ctrl_range: ", l_ctrl_range)

        self.ctrl = np.zeros(self.nu)
        self._set_init_state()

        EE_NAME  = self.site("ee_center_site")
        _site_dict = self.query_site_pos_and_quat([EE_NAME])
        self._initial_grasp_site_xpos = _site_dict[EE_NAME]['xpos']
        self._initial_grasp_site_xquat = _site_dict[EE_NAME]['xquat']
        self._saved_xpos = self._initial_grasp_site_xpos
        self._saved_xquat = self._initial_grasp_site_xquat

        self.set_grasp_mocap(self._initial_grasp_site_xpos, self._initial_grasp_site_xquat)

        EE_NAME_R  = self.site("ee_center_site_r")
        _site_dict_r = self.query_site_pos_and_quat([EE_NAME_R])
        self._initial_grasp_site_xpos_r = _site_dict_r[EE_NAME_R]['xpos']
        self._initial_grasp_site_xquat_r = _site_dict_r[EE_NAME_R]['xquat']

        self.set_grasp_mocap_r(self._initial_grasp_site_xpos_r, self._initial_grasp_site_xquat_r)
        
        self._pico_joystick = PicoJoystick()

        self._r_controller_config = controller_config.load_config("osc_pose")
        # print("controller_config: ", self.controller_config)

        # Add to the controller dict additional relevant params:
        #   the robot name, mujoco sim, eef_name, joint_indexes, timestep (model) freq,
        #   policy (control) freq, and ndim (# joints)
        self._r_controller_config["robot_name"] = agent_names[0]
        self._r_controller_config["sim"] = self.gym
        self._r_controller_config["eef_name"] = EE_NAME_R
        # self.controller_config["eef_rot_offset"] = self.eef_rot_offset
        qpos_offsets, qvel_offsets, _ = self.query_joint_offsets(self._r_arm_joint_names)
        self._r_controller_config["joint_indexes"] = {
            "joints": self._r_arm_joint_names,
            "qpos": qpos_offsets,
            "qvel": qvel_offsets,
        }
        self._r_controller_config["actuator_range"] = r_ctrl_range
        self._r_controller_config["policy_freq"] = self.control_freq
        self._r_controller_config["ndim"] = len(self._r_arm_joint_names)
        self._r_controller_config["control_delta"] = False


        self._r_controller = controller_factory(self._r_controller_config["type"], self._r_controller_config)
        self._r_controller.update_initial_joints(self._r_neutral_joint_values)

        self._l_controller_config = controller_config.load_config("osc_pose")
        # print("controller_config: ", self.controller_config)

        # Add to the controller dict additional relevant params:
        #   the robot name, mujoco sim, eef_name, joint_indexes, timestep (model) freq,
        #   policy (control) freq, and ndim (# joints)
        self._l_controller_config["robot_name"] = agent_names[0]
        self._l_controller_config["sim"] = self.gym
        self._l_controller_config["eef_name"] = EE_NAME
        # self.controller_config["eef_rot_offset"] = self.eef_rot_offset
        qpos_offsets, qvel_offsets, _ = self.query_joint_offsets(self._l_arm_joint_names)
        self._l_controller_config["joint_indexes"] = {
            "joints": self._l_arm_joint_names,
            "qpos": qpos_offsets,
            "qvel": qvel_offsets,
        }
        self._l_controller_config["actuator_range"] = l_ctrl_range
        self._l_controller_config["policy_freq"] = self.control_freq
        self._l_controller_config["ndim"] = len(self._l_arm_joint_names)
        self._l_controller_config["control_delta"] = False


        self._l_controller = controller_factory(self._l_controller_config["type"], self._l_controller_config)
        self._l_controller.update_initial_joints(self._l_neutral_joint_values)


    def _set_init_state(self) -> None:
        # print("Set initial state")
        self.set_joint_neutral()

        self.ctrl = np.zeros(self.nu)       
        self.set_ctrl(self.ctrl)
        self.mj_forward()


    def step(self, action) -> tuple[ObsType, SupportsFloat, bool, bool, dict[str, Any]]:
        self._set_action()
        self.do_simulation(self.ctrl, self.frame_skip)
        obs = self._get_obs().copy()

        info = {}
        terminated = False
        truncated = False
        reward = 0

        return obs, reward, terminated, truncated, info
    
    def _set_gripper_ctrl(self, joystick_state) -> None:
        trigger_value = joystick_state["leftHand"]["triggerValue"]  # Value in [0, 1]
        
        # Adjust sensitivity using an exponential function
        k = 5  # Adjust 'k' to change the curvature of the exponential function
        adjusted_value = (np.exp(k * trigger_value) - 1) / (np.exp(k) - 1)  # Maps input from [0, 1] to [0, 1]
        offset_rate = -adjusted_value

        for actuator_id in self._l_hand_actuator_id:
            actuator_name = self.model.actuator_id2name(actuator_id)
            if actuator_name == self.actuator("M_zbll_J2") or actuator_name == self.actuator("M_zbll_J3"):
                offset_rate *= -1

            abs_ctrlrange = self._all_ctrlrange[actuator_id][1] - self._all_ctrlrange[actuator_id][0]
            self.ctrl[actuator_id] = offset_rate * abs_ctrlrange
            self.ctrl[actuator_id] = np.clip(
                self.ctrl[actuator_id],
                self._all_ctrlrange[actuator_id][0],
                self._all_ctrlrange[actuator_id][1])

    def _set_gripper_ctrl_r(self, joystick_state) -> None:
        trigger_value = joystick_state["rightHand"]["triggerValue"]  # Value in [0, 1]
        
        # Adjust sensitivity using an exponential function
        k = 5  # Adjust 'k' to change the curvature of the exponential function
        adjusted_value = (np.exp(k * trigger_value) - 1) / (np.exp(k) - 1)  # Maps input from [0, 1] to [0, 1]
        offset_rate = -adjusted_value

        for actuator_id in self._r_hand_actuator_id:
            actuator_name = self.model.actuator_id2name(actuator_id)
            if actuator_name == self.actuator("M_zbr_J2") or actuator_name == self.actuator("M_zbr_J3"):
                offset_rate *= -1

            abs_ctrlrange = self._all_ctrlrange[actuator_id][1] - self._all_ctrlrange[actuator_id][0]
            self.ctrl[actuator_id] = offset_rate * abs_ctrlrange
            self.ctrl[actuator_id] = np.clip(
                self.ctrl[actuator_id],
                self._all_ctrlrange[actuator_id][0],
                self._all_ctrlrange[actuator_id][1])
        # offset_rate = -joystick_state["rightHand"]["triggerValue"]
        # print("offset_rate: ", offset_rate)

        # for actuator_id in self._r_hand_actuator_id:
        #     if self.model.actuator_id2name(actuator_id) == self.actuator("M_zbr_J2") or self.model.actuator_id2name(actuator_id) == self.actuator("M_zbr_J3"):
        #         offset_rate *= -1

        #     abs_ctrlrange = self._all_ctrlrange[actuator_id][1] - self._all_ctrlrange[actuator_id][0]
        #     self.ctrl[actuator_id] = offset_rate * abs_ctrlrange
        #     self.ctrl[actuator_id] = np.clip(self.ctrl[actuator_id], self._all_ctrlrange[actuator_id][0], self._all_ctrlrange[actuator_id][1])

    def _load_record(self) -> None:
        if self.record_file is None:
            raise ValueError("record_file is not set.")
        
        # 读取record_file中的数据，存储到record_pool中
        with h5py.File(self.record_file, 'r') as f:
            if "float_data" in f:
                dset = f["float_data"]
                if self.record_cursor >= dset.shape[0]:
                    return False

                self.record_pool = dset[self.record_cursor:self.record_cursor + self.RECORD_POOL_SIZE].tolist()
                self.record_cursor += self.RECORD_POOL_SIZE
                return True

        return False
    
    def save_record(self) -> None:
        if self.record_state != RecordState.RECORD:
            return
        
        if self.record_file is None:
            raise ValueError("record_file is not set.")

        with h5py.File(self.record_file, 'a') as f:
            # 如果数据集存在，获取其大小；否则，创建新的数据集
            if "float_data" in f:
                dset = f["float_data"]
                self.record_cursor = dset.shape[0]
            else:
                dset = f.create_dataset("float_data", (0, len(self.ctrl)), maxshape=(None, len(self.ctrl)), dtype='f', compression="gzip")
                self.record_cursor = 0

            # 将record_pool中的数据写入数据集
            dset.resize((self.record_cursor + len(self.record_pool), len(self.ctrl)))
            dset[self.record_cursor:] = np.array(self.record_pool)
            self.record_cursor += len(self.record_pool)
            self.record_pool.clear()

            print("Record saved.")


    def _replay(self) -> None:
        if self.record_state == RecordState.REPLAY_FINISHED:
            return
        
        if len(self.record_pool) == 0:
            if not self._load_record():
                self.record_state = RecordState.REPLAY_FINISHED
                print("Replay finished.")
                return

        self.ctrl = self.record_pool.pop(0)

    def _set_action(self) -> None:
        if self.record_state == RecordState.REPLAY or self.record_state == RecordState.REPLAY_FINISHED:
            self._replay()
            return

        mocap_l_xpos, mocap_l_xquat, mocap_r_xpos, mocap_r_xquat = None, None, None, None

        if self._pico_joystick is not None:
            mocap_l_xpos, mocap_l_xquat, mocap_r_xpos, mocap_r_xquat = self._processe_pico_joystick_move()
            self.set_grasp_mocap(mocap_l_xpos, mocap_l_xquat)
            self.set_grasp_mocap_r(mocap_r_xpos, mocap_r_xquat)
            self._process_pico_joystick_operation()
            # print("base_body_euler: ", self._base_body_euler / np.pi * 180)
        else:
            return


        # 两个工具的quat不一样，这里将 qw, qx, qy, qz 转为 qx, qy, qz, qw
        mocap_r_axisangle = transform_utils.quat2axisangle(np.array([mocap_r_xquat[1], 
                                                                   mocap_r_xquat[2], 
                                                                   mocap_r_xquat[3], 
                                                                   mocap_r_xquat[0]]))              
        # mocap_axisangle[1] = -mocap_axisangle[1]
        action_r = np.concatenate([mocap_r_xpos, mocap_r_axisangle])
        # print("action r:", action_r)
        self._r_controller.set_goal(action_r)
        ctrl = self._r_controller.run_controller()
        # print("ctrl r: ", ctrl)
        for i in range(len(self._r_arm_actuator_id)):
            self.ctrl[self._r_arm_actuator_id[i]] = ctrl[i]


        mocap_l_axisangle = transform_utils.quat2axisangle(np.array([mocap_l_xquat[1], 
                                                                   mocap_l_xquat[2], 
                                                                   mocap_l_xquat[3], 
                                                                   mocap_l_xquat[0]]))  
        action_l = np.concatenate([mocap_l_xpos, mocap_l_axisangle])
        # print("action l:", action_l)        
        # print(action)
        self._l_controller.set_goal(action_l)
        ctrl = self._l_controller.run_controller()
        # print("ctrl l: ", ctrl)
        for i in range(len(self._l_arm_actuator_id)):
            self.ctrl[self._l_arm_actuator_id[i]] = ctrl[i]
        
        # print("ctrl: ", self.ctrl)

        # 将控制数据存储到record_pool中
        if self.record_state == RecordState.RECORD:
            self._save_record()

    def _processe_pico_joystick_move(self):
        if self._pico_joystick.is_reset_pos():
            self._pico_joystick.set_reset_pos(False)
            self._set_init_state()

        transform_list = self._pico_joystick.get_transform_list()
        if transform_list is None:
            return self._initial_grasp_site_xpos, self._initial_grasp_site_xquat, self._initial_grasp_site_xpos_r, self._initial_grasp_site_xquat_r

        left_relative_position, left_relative_rotation = self._pico_joystick.get_left_relative_move(transform_list)
        right_relative_position, right_relative_rotation = self._pico_joystick.get_right_relative_move(transform_list)

        # left_relative_position_org, left_relative_rotation_org = self._pico_joystick.get_left_relative_move_org(transform_list)
        # right_relative_position_org, right_relative_rotation_org = self._pico_joystick.get_right_relative_move_org(transform_list)

        # print("left_relative_position: ", left_relative_position)
        # print("left_relative_rotation: ", rotations.quat2euler(left_relative_rotation) * 180 / np.pi)
        # print("right_relative_position: ", right_relative_position)
        # print("right_relative_rotation: ", R.from_quat(right_relative_rotation, scalar_first=True).as_euler('xzy', degrees=True))
        # print("right_relative_rotation_org: ", R.from_quat(right_relative_rotation_org, scalar_first=True).as_euler('xzy', degrees=True))

        # def decompose(quat):
        #     v = R.from_quat(quat, scalar_first=True).as_rotvec(degrees=True)
        #     l = np.linalg.norm(v)
        #     v = v / l
        #     return [f'{v[0]:>12.6f} {v[1]:>12.6f} {v[2]:>12.6f}', l]
        

            # v = R.from_quat(quat, scalar_first=True).as_euler('zxy', degrees=True)
            # return f'{v[0]:>12.6f} {v[1]:>12.6f} {v[2]:>12.6f}'

        # print("rotation_org: ", decompose(right_relative_rotation_org))
        # print("rotation_mujo:", decompose(right_relative_rotation))

        mocap_l_xpos = self._initial_grasp_site_xpos + rotations.quat_rot_vec(self._base_body_xquat, left_relative_position)
        mocap_r_xpos = self._initial_grasp_site_xpos_r + rotations.quat_rot_vec(self._base_body_xquat, right_relative_position)

        mocap_l_xquat = rotations.quat_mul(self._initial_grasp_site_xquat, left_relative_rotation)
        # mocap_r_xquat = rotations.quat_mul(self._initial_grasp_site_xquat_r, right_relative_rotation)
        mocap_r_xquat = (R.from_quat(self._initial_grasp_site_xquat_r, scalar_first=True) * 
                         R.from_quat(right_relative_rotation, scalar_first=True)).as_quat(scalar_first=True, canonical=True)
        
   

        return mocap_l_xpos, mocap_l_xquat, mocap_r_xpos, mocap_r_xquat


    def _process_pico_joystick_operation(self):
        joystick_state = self._pico_joystick.get_key_state()
        if joystick_state is None:
            return

        self._set_gripper_ctrl_r(joystick_state)
        self._set_gripper_ctrl(joystick_state)

    def _save_record(self) -> None:
        self.record_pool.append(self.ctrl.copy())   
        if (len(self.record_pool) >= self.RECORD_POOL_SIZE):
            self.save_record()

    def _get_obs(self) -> dict:
        # robot
        EE_NAME = self.site("ee_center_site")
        ee_position = self.query_site_pos_and_quat([EE_NAME])[EE_NAME]['xpos'].copy()
        ee_xvalp, _ = self.query_site_xvalp_xvalr([EE_NAME])
        ee_velocity = ee_xvalp[EE_NAME].copy() * self.dt


        achieved_goal = np.zeros(3)
        desired_goal = self.goal.copy()
        obs = np.concatenate(
                [
                    ee_position,
                    ee_velocity,
                    np.zeros(1),
                ]).copy()            
        result = {
            "observation": obs,
            "achieved_goal": achieved_goal,
            "desired_goal": desired_goal,
        }
        return result

    def _render_callback(self) -> None:
        pass

    def reset_model(self):
        # Robot_env 统一处理，这里实现空函数就可以
        pass

    def _reset_sim(self) -> bool:
        self._set_init_state()
        self.set_grasp_mocap(self._initial_grasp_site_xpos, self._initial_grasp_site_xquat)
        self.set_grasp_mocap_r(self._initial_grasp_site_xpos_r, self._initial_grasp_site_xquat_r)
        self.mj_forward()

        print("""
              To use VR controllers, please press both B and Y buttons to connect / disconnect to the simulator.
              And then press A and X buttons to reset the robot's hands to the initial position.
              """)        
        return True

    # custom methods
    # -----------------------------
    def set_grasp_mocap(self, position, orientation) -> None:
        mocap_pos_and_quat_dict = {self.mocap("leftHandMocap"): {'pos': position, 'quat': orientation}}
        self.set_mocap_pos_and_quat(mocap_pos_and_quat_dict)

    def set_grasp_mocap_r(self, position, orientation) -> None:
        mocap_pos_and_quat_dict = {self.mocap("rightHandMocap"): {'pos': position, 'quat': orientation}}
        # print("Set grasp mocap: ", position, orientation)
        self.set_mocap_pos_and_quat(mocap_pos_and_quat_dict)

    def set_goal_mocap(self, position, orientation) -> None:
        mocap_pos_and_quat_dict = {"goal_goal": {'pos': position, 'quat': orientation}}
        self.set_mocap_pos_and_quat(mocap_pos_and_quat_dict)

    def set_joint_neutral(self) -> None:
        # assign value to arm joints
        arm_joint_qpos_list = {}
        for name, value in zip(self._r_arm_joint_names, self._r_neutral_joint_values):
            arm_joint_qpos_list[name] = np.array([value])
        for name, value in zip(self._l_arm_joint_names, self._l_neutral_joint_values):
            arm_joint_qpos_list[name] = np.array([value])     
        self.set_joint_qpos(arm_joint_qpos_list)
        # print("set init joint state: " , arm_joint_qpos_list)
        # assign value to finger joints
        # gripper_joint_qpos_list = {}
        # for name, value in zip(self._gripper_joint_names, self._neutral_joint_values[7:9]):
        #     gripper_joint_qpos_list[name] = np.array([value])
        # self.set_joint_qpos(gripper_joint_qpos_list)

    def _sample_goal(self) -> np.ndarray:
        # 训练reach时，任务是移动抓夹，goal以抓夹为原点采样
        goal = np.array([0, 0, 0])
        return goal


    def get_ee_xform(self) -> np.ndarray:
        pos_dict = self.query_site_pos_and_mat([self.site("ee_center_site")])
        xpos = pos_dict[self.site("ee_center_site")]['xpos'].copy()
        xmat = pos_dict[self.site("ee_center_site")]['xmat'].copy().reshape(3, 3)
        return xpos, xmat

