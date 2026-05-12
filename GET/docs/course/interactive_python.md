# Interactive Python

Students can use Python interactively in two supported ways.

## A. Use JupyterHub Directly

Use the standard server JupyterHub environment for notebooks, plots, and downstream analysis that does not require the GET container Python packages.

Open a JupyterHub terminal and start from the course module:

```bash
cd ~/AI_in_genomics/GET
bash scripts/course_00_check_environment.sh
```

Keep generated notebooks and analysis outputs in `~/GET_course_work`, not in the Git checkout.

## B. Use the GET Container Kernel

If a notebook needs the exact GET Python environment, install the user-local JupyterHub kernel once:

```bash
cd ~/AI_in_genomics/GET
bash scripts/course_install_container_kernel.sh
```

Then restart the JupyterHub server from the Hub control panel, open a new Launcher, and choose:

```text
GET container (course)
```

This keeps the normal JupyterHub interface, but runs the notebook kernel inside the GET Apptainer container.
