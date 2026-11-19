# CollisionsOP User Manual

**CollisionsOP: Linear Momentum Conservation Simulator** is an interactive 2D educational program for exploring momentum in collisions. It models planets and asteroids as circular bodies and displays the system's momentum and kinetic energy while the simulation runs.

The simulation uses simplified, illustrative parameters for classroom demonstrations. It is not intended for precise astrophysical calculations.

## Requirements

- Python 3
- Pygame installed in the same Python environment used to run the program
- The program source file, named `colisiones_OP.py` in the accompanying documentation
- A display that can accommodate a window of approximately 1240 × 720 pixels

## Installation and launch

1. Install Python 3 and confirm it is available from a terminal:

   ```sh
   python --version
   ```

   On some systems, use `python3 --version` instead.

2. Install Pygame:

   ```sh
   python -m pip install pygame
   ```

3. Place `colisiones_OP.py` in a folder where you can read and run it.
4. From that folder, launch the simulator:

   ```sh
   python colisiones_OP.py
   ```

   In Spyder, open the file and press **F5**. If the simulation window does not appear in front of Spyder, check the taskbar.

## Quick start

The simulator starts with experiment 1. The simulation occupies the left side of the window, and a numerical information panel appears on the right. Watch the bodies collide, then compare the momentum and energy values before and after the collision. Press **R** to reset the current experiment.

To create a body, click and drag in the simulation area. The drag direction and length set its initial velocity. Adjust the radius before creating a body with the mouse wheel or the **+** and **-** keys.

## Controls

| Input | Action |
| --- | --- |
| Left-click and drag | Create and launch a body; the drag sets its initial velocity. |
| Right-click | Delete the selected body. |
| Mouse wheel or **+** / **-** | Increase or decrease the radius, and therefore the mass, of the next body. |
| **0** to **6** | Load the empty workspace or one of the six preset experiments. |
| **R** | Reset the current experiment. |
| **Space** | Pause or resume. |
| **S** | Cycle through time factors 1, 0.5, and 0.25. |
| **M** | Cycle between elastic collision, inelastic collision, and merging modes. |
| **Up / Down arrows** | Select inelastic mode and change the coefficient of restitution, *e*, in increments of 0.05. |
| **G** | Turn mutual gravity on or off. |
| **B** | Turn boundary walls on or off. |
| **V** | Show or hide velocity vectors. |
| **P** | Show or hide momentum vectors. |
| **T** | Show or hide trails. |
| **C** | Switch between the laboratory view and center-of-mass tracking view. |
| **H** | Show or hide the help display. |
| **Esc** | Exit. |

## Preset experiments

Use the number keys to load an experiment:

| Key | Experiment | What to observe |
| --- | --- | --- |
| **0** | Empty workspace | Create bodies and set up a custom experiment. |
| **1** | Head-on elastic collision with equal masses | The bodies exchange velocities. |
| **2** | Asteroid colliding with a stationary planet | Observe a one-dimensional collision between unequal masses. |
| **3** | Oblique billiard-ball collision | Compare momentum conservation along the *x* and *y* axes. |
| **4** | Partially inelastic collision, *e* = 0.5 | Observe conserved momentum and reduced kinetic energy. |
| **5** | Asteroid and planet merging | Observe the combined body's mass and velocity after merging. |
| **6** | Gravitational cluster | Observe mutual gravity, accretion, and a system initialized with zero total momentum. |

## Understanding the information panel

The panel reports each body's mass, velocity, and momentum, followed by system totals and recent history. In particular, it shows:

- Total mass and the total momentum components, *p*<sub>x</sub> and *p*<sub>y</sub>, as well as the magnitude of total momentum.
- Total kinetic energy and energy dissipated in collisions.
- The residual between the measured total momentum and the expected momentum balance.
- A summary of the most recent collision, including values before and after impact.
- Recent time plots of total *p*<sub>x</sub>, total *p*<sub>y</sub>, the magnitude of total momentum, and total kinetic energy. Orange vertical lines mark collisions.

## Collision model

Collisions are frictionless and are resolved using an impulse along the contact normal. The coefficient of restitution *e* controls the collision:

- *e* = 1: elastic collision.
- 0 ≤ *e* < 1: inelastic collision, with less kinetic energy in the relative normal motion.
- Merge mode: the two bodies become one body whose mass is the sum of the original masses. Its velocity is set to conserve their combined momentum.

The simulator uses the internal relation *m* = *ρr*³ for mass, where *ρ* is the configured density and *r* is the body's radius.

## Suggested activities

1. **Check momentum in an elastic collision:** Load experiment 1 and observe that changes in total momentum and kinetic energy are close to zero, subject to numerical error.
2. **Compare inelastic collisions:** Load experiment 4 and vary *e*. Momentum should remain conserved while the energy loss increases as *e* decreases.
3. **Study merging:** Load experiment 5 and compare total mass and momentum before and after the merge.
4. **Explore internal forces:** Load experiment 6 with gravity enabled and observe whether total momentum stays close to zero.
5. **Explore external impulses:** Turn on walls with **B** and compare the change in momentum with the accumulated external impulse.

## Troubleshooting and limitations

- **`ModuleNotFoundError: No module named 'pygame'`:** Install Pygame into the same Python environment that runs the script.
- **The window is hidden in Spyder:** Select it from the taskbar. Avoid running multiple instances at once.
- **Performance slows with many bodies:** Collision detection checks every pair of bodies, so its work grows approximately with the square of the number of bodies.
- **Gravity results are not precise:** Gravity uses explicit integration and softening for stability and visibility; it is not designed for precision astrophysics.
- **Bodies leave the visible area:** This can happen when boundary walls are disabled. The program indicates off-screen bodies at the edge.
- **Random cluster differs between runs:** The cluster uses random initial conditions; the current version does not guarantee a fixed random seed.

## Software structure

The program is organized around four logical components:

- `Cuerpo` stores a body's mechanical state, including position, velocity, radius, mass, momentum, and kinetic energy.
- `Mundo` manages bodies, physical time, integration, gravity, walls, collisions, merging, and momentum accounting.
- `Camara` converts between simulation and screen coordinates and supports laboratory and center-of-mass views.
- `Juego` handles Pygame initialization, input, scenarios, timing, interface, plots, and the main loop.

## Notes for contributors

The documentation supplied with this project identifies `colisiones_OP.py` as the program entry point. Check that the source file and its dependencies are included in the repository, and update this manual if filenames, controls, or behavior change.
