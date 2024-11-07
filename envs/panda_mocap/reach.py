import os
from .panda_env import FrankaEnv

class FrankaReachEnv(FrankaEnv):
    def __init__(
        self,
        frame_skip: int,                
        reward_type: str,
        orcagym_addr: str,
        agent_names: list[str],
        time_step: float,  
        **kwargs,
    ):
        super().__init__(
            frame_skip=frame_skip,
            orcagym_addr=orcagym_addr,
            agent_names=agent_names,
            time_step=time_step,
            reward_type=reward_type,
            has_object=False,
            block_gripper=True,
            distance_threshold=0.05,
            goal_xy_range=0.5,
            obj_xy_range=0.3,
            goal_x_offset=0.0,
            goal_z_range=0.3,
            **kwargs,
        )
