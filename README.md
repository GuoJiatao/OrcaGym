# OrcaGym Project
Welcome to the OrcaGym project! OrcaGym is an enhanced simulation environment based on the OpenAI Gymnasium framework, designed for seamless integration with existing OpenAI Gym simulation environments and algorithms. Developed by Songying Technology, OrcaStudio offers robust support for various physics engines and ray-tracing rendering, delivering both physical and visual precision. This document serves as an introduction to OrcaGym, its background, purpose, usage, and important considerations.

## Background
In the realm of robotics simulation, having a versatile and accurate environment is crucial for developing and testing algorithms. OpenAI Gym has been a cornerstone in this space, providing a standardized interface for reinforcement learning (RL) tasks. However, the need for more advanced features, such as support for multiple physics engines and high-fidelity rendering, led to the development of OrcaStudio. OrcaGym bridges the gap between OpenAI Gym and OrcaStudio, enabling researchers and developers to leverage the advanced capabilities of OrcaStudio while maintaining compatibility with OpenAI Gym environments and algorithms.

## Purpose
The primary goal of OrcaGym is to enhance the capabilities of OpenAI Gym by integrating it with the OrcaStudio simulation platform. This integration allows users to:

1. Leverage Multiple Physics Engines: OrcaStudio supports Mujoco, PhysX, ODE, and more, providing users with flexibility in choosing the most suitable physics engine for their tasks.
2. Achieve High-Fidelity Rendering: With ray-tracing support, OrcaStudio offers visually precise simulations, essential for tasks requiring accurate visual feedback.
3. Enable Distributed Deployment: OrcaGym and OrcaStudio can run on the same node or across different nodes, facilitating distributed deployment and large-scale AI cluster training.

## Features
* **Compatibility with OpenAI Gym:** Seamless integration with existing OpenAI Gym environments and algorithms.
* **Multi-Physics Engine Support:** Choose from Mujoco, PhysX, ODE, and more.
* **High-Fidelity Rendering:** Ray-tracing support for precise visual simulations.
* **Distributed Deployment:** Run simulations on the same or different nodes, supporting large-scale AI training.
* **Ease of Use:** Simple interface to transition from OpenAI Gym to OrcaGym.

## Installation
To install OrcaGym, follow these steps:

1. **Clone the Repository:**

```bash
git clone https://github.com/openverse-orca/OrcaGym.git
cd OrcaGym
```

2. **Install Dependencies:**

To facilitate quick installation, we can create a new Conda environment: (If you do not have anaconda installed, please go to the [official website](https://www.anaconda.com/) to install it)
```bash
conda create --name orca_gym_test python=3.11
conda activate orca_gym_test
```

Then install the dependencies in the newly created environment:
```bash
pip install -r requirements.txt
```

2. **Install PyTorch:**

Using a combination of PyTorch and CUDA can effectively speed up reinforcement learning training. Install the corresponding CUDA package based on your GPU device. Here is an example:
```bash
pip install torch==2.3.1+cu121 -f https://download.pytorch.org/whl/torch_stable.html
```

## Set Up OrcaStudio:

Follow the instructions provided in the [OrcaStudio documentation](URL:http://orca3d.cn/) to install and configure OrcaStudio on your system.

## Usage
Using OrcaGym is straightforward. Here are the examples to get you started:

* **Copy the Files**: Copy the files (levels, assets) from the `orca-studio-projects` directory to your OrcaStudio installation directory. Assuming your installation directory is `$MyWorkSpace/OrcaStudio`, then copy the files to `$MyWorkSpace/OrcaStudio/Projects/OrcaProject` directory.

* **Validate OrcaGym Environment:**
    * **Launch OrcaStudio**: Launch OrcaStudio and load the corresponding level, for example `Ant_Multiagent`. Click the "Start" button (Ctrl-G) to enter Game Play mode.
    * **Follow the Guide**: Follow the instructions in the `tutorial/GymEnvTest.ipynb` document to validate the basic functionality.

* **OrcaGym's Mujoco Interface**
    * **Launch OrcaStudio**: Launch OrcaStudio and load the `Humanoid_LQR` level. Click the "Start" button (Ctrl-G) to enter Game Play mode.
    * **Follow the Guide**: Follow the instructions in `tutorial/Humanoid-LQR.ipynb` to learn how to port the LQR example included in the Mujoco project into OrcaGym.

* **Control the Franka Panda Robot Arm with an Xbox Controller**
    * **Launch OrcaStudio**: Launch OrcaStudio and load the `Franka_Joystick` level. Click the "Start" button (Ctrl-G) to enter Game Play mode.
    * **Follow the Guide**: Follow the instructions in `tutorial/Xbox-Joystick-Control.ipynb` to learn how to control the Franka Panda robot arm using the controller, and implement operation recording and replay.

* **Reinforcement Learning Training Example**
    * **Launch OrcaStudio**: Launch OrcaStudio and load the `FrankaPanda_RL` level. Click the "Start" button (Ctrl-G) to enter Game Play mode.
    * **Follow the Guide**: Follow the instructions in `tutorial/FrankaPanda-RL/FrankaPanda-RL.ipynb` to learn how to use multi-agent reinforcement learning training.


## Important Considerations
* Performance: High-fidelity rendering and complex physics simulations can be computationally intensive. Ensure your hardware meets the requirements for running OrcaStudio effectively.
* Configuration: Properly configure OrcaStudio to match your simulation needs. Refer to the OrcaStudio documentation for detailed configuration options.
* Compatibility: While OrcaGym aims for compatibility with OpenAI Gym, some advanced features may require additional configuration or modification of existing Gym environments.

## Contributing
We welcome contributions to the OrcaGym project. If you have suggestions, bug reports, or feature requests, please open an issue or submit a pull request on our GitHub repository.

## License
OrcaGym is licensed under the MIT License. See the LICENSE file for more information.

## Contact
For any inquiries or support, please contact us at huangwei@openverse.com.cn

---

We hope you find OrcaGym a valuable tool for your robotics and reinforcement learning research. Happy simulating!
