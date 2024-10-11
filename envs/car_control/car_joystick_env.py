from envs.robot_env import MujocoRobotEnv
from orca_gym.utils import rotations
from typing import Optional, Any, SupportsFloat
from gymnasium import spaces
from orca_gym.devices.xbox_joystick import XboxJoystick, XboxJoystickManager  # 引入 XboxJoystick 和 XboxJoystickManager
import numpy as np
import h5py
ObsType = Any

class RecordState:
    RECORD = "record"
    REPLAY = "replay"
    REPLAY_FINISHED = "replay_finished"
    NONE = "none"

class CarEnv(MujocoRobotEnv):
    """
    通过xbox手柄控制汽车模型
    """
    def __init__(
        self,
        frame_skip: int = 5,
        grpc_address: str = 'localhost:50051',
        agent_names: list = ['Agent0'],
        time_step: float = 0.016,  # 0.016 for 60 fps
        record_state: str = RecordState.NONE,
        record_file: Optional[str] = None,
        **kwargs,
    ):

        action_size = 2  # 这里的 action size 根据汽车控制的需求设置
        self.ctrl = np.zeros(action_size)  # 提前初始化self.ctrl
        self.n_actions = 2  # 示例值；根据你的动作空间进行调整
        self.record_state = record_state
        self.record_file = record_file
        self.record_pool = []
        self.RECORD_POOL_SIZE = 1000
        self.record_cursor = 0

        super().__init__(
            frame_skip=frame_skip,
            grpc_address=grpc_address,
            agent_names=agent_names,
            time_step=time_step,
            n_actions=action_size,
            observation_space=None,
            **kwargs,
        )

        # 初始化手柄管理器
        self.joystick_manager = XboxJoystickManager()
        # 从手柄管理器中获取第一个手柄（假设只使用一个手柄）
        self.joystick = self.joystick_manager.get_joystick(self.joystick_manager.get_joystick_names()[0])

        # 定义初始位置和其他状态信息
        self._set_init_state()

    def _set_init_state(self) -> None:
        # 初始化控制变量
        self.ctrl = np.zeros(self.n_actions)  # 确保与动作空间匹配
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

    def control_step(self, joystick_input):
        """
        根据手柄输入控制小车的左右轮
        """
        SPEED_FACTOR = 1.0  # 速度调节因子，可根据需要调整
        
        # 左摇杆控制左轮，右摇杆控制右轮
        left_wheel_force = joystick_input["axes"]["LeftStickY"] * SPEED_FACTOR
        right_wheel_force = joystick_input["axes"]["RightStickY"] * SPEED_FACTOR
        
        # 返回左轮和右轮的控制力矩
        return np.array([left_wheel_force, right_wheel_force])

    def _capture_joystick_ctrl(self, joystick_state) -> np.ndarray:
        """
        获取手柄输入并返回控制量
        """
        ctrl = self.control_step(joystick_state)
        return ctrl

    def _set_action(self) -> None:
        """
        根据手柄输入更新小车的控制量
        """
        if self.record_state == RecordState.REPLAY or self.record_state == RecordState.REPLAY_FINISHED:
            self._replay()
            return

        # 调用 Joystick Manager 更新手柄状态
        self.joystick_manager.update()  # 由 Joystick Manager 更新所有手柄状态

        # 获取 joystick 的状态
        joystick_state = self.joystick.get_state()  # 获取 XboxJoystick 实例的状态

        # 获取控制量并应用
        ctrl = self._capture_joystick_ctrl(joystick_state)  # 将状态传递给控制捕获函数
        self.ctrl = ctrl

        # 如果在录制状态，保存记录
        if self.record_state == RecordState.RECORD:
            self._save_record()

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

    def _save_record(self) -> None:
        self.record_pool.append(self.ctrl.copy())
        if len(self.record_pool) >= self.RECORD_POOL_SIZE:
            self.save_record()

    def _get_obs(self) -> dict:
        # 这里根据你的汽车模型获取观察数据
        obs = np.concatenate([self.ctrl]).copy()
        result = {
            "observation": obs,
            "achieved_goal": np.array([0, 0]),
            "desired_goal": np.array([0, 0]),
        }
        return result

    def reset_model(self):
        self._set_init_state()

    def _reset_sim(self) -> bool:
        self._set_init_state()
        return True

    def _sample_goal(self):
        return np.zeros((self.model.nq,))  # 例如，返回一个全零的目标