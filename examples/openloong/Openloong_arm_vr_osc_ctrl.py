import os
import sys
import time

current_file_path = os.path.abspath('./../../')

if current_file_path not in sys.path:
    print("add path: ", current_file_path)
    sys.path.append(current_file_path)


import gymnasium as gym
from gymnasium.envs.registration import register
from datetime import datetime

# 
TIME_STEP = 0.01

def register_env(grpc_address, control_freq=20):
    print("register_env: ", grpc_address)
    gym.register(
        id=f"XboxControl-v0-OrcaGym-{grpc_address[-2:]}",
        entry_point="envs.openloong.Openloong_arm_vr_env:OpenloongArmEnv",
        kwargs={'frame_skip': 1,   
                'reward_type': "dense",
                'grpc_address': grpc_address, 
                'agent_names': ['AzureLoong'], 
                'time_step': TIME_STEP,
                'control_freq': control_freq},
        max_episode_steps=sys.maxsize,
        reward_threshold=0.0,
    )

def continue_training(env):
    observation, info = env.reset(seed=42)
    print("""
        To use VR controllers, please press left joystick to connect / disconnect to the simulator.
        And then press right joystick to reset the robot's hands to the initial position.
        """)  
    while True:
        start_time = datetime.now()

        action = env.action_space.sample()
        observation, reward, terminated, truncated, info = env.step(action)

        elapsed_time = datetime.now() - start_time
        if elapsed_time.total_seconds() < TIME_STEP:
            time.sleep(TIME_STEP - elapsed_time.total_seconds())

    

if __name__ == "__main__":
    """
    OSC运动算法控制青龙机器人机械臂的示例
    """
    try:
        grpc_address = "localhost:50051"
        print("simulation running... , grpc_address: ", grpc_address)
        env_id = f"XboxControl-v0-OrcaGym-{grpc_address[-2:]}"

        register_env(grpc_address, 20)

        env = gym.make(env_id)        
        print("Starting simulation...")

        continue_training(env)
    except KeyboardInterrupt:
        print("Simulation stopped")        
        env.close()