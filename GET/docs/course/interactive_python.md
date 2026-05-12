# Interactive Python

Students can use Python interactively in two ways. Both should keep large generated files in `~/GET_course_work`, not in the Git checkout.

## Option A: JupyterHub

Use the server JupyterHub for normal course work, editing notebooks, plotting results, and writing analysis code. It is the standard entry point to the teaching server.

Open a JupyterHub terminal and start from the course module:

```bash
cd ~/AI_in_genomics/GET
bash scripts/course_00_check_environment.sh
```

From JupyterHub notebooks, use the same course paths as the shell scripts:

```python
from pathlib import Path
import os

HOME = Path.home()
os.environ.setdefault("GET_COURSE_DATA", str(HOME / "GET_course_data"))
os.environ.setdefault("GET_COURSE_WORK", str(HOME / "GET_course_work"))

course_work = Path(os.environ["GET_COURSE_WORK"])
zarr_path = course_work / "multiome_1" / "preprocessed" / "multiome1_human.zarr"
```

JupyterHub is usually the best choice for downstream analysis after inference. If a notebook needs the exact GET Python environment, use the container option below.

## Option B: Jupyter Lab in the GET container

This starts Jupyter Lab with the same Python packages used by the preprocessing, zarr, fine-tuning, and inference wrappers.

```bash
cd ~/AI_in_genomics/GET
bash scripts/course_jupyter_lab_container.sh
```

The script uses these defaults:

```bash
GET_JUPYTER_IP=127.0.0.1
GET_JUPYTER_PORT=8888
GET_JUPYTER_DIR=$HOME
```

If port `8888` is busy, choose another port:

```bash
export GET_JUPYTER_PORT=8891
bash scripts/course_jupyter_lab_container.sh
```

If you connect from your laptop by SSH, open a tunnel in a second terminal before opening the Jupyter URL:

```bash
ssh -L 8888:127.0.0.1:8888 <user>@<teaching-server>
```

Then open the `http://127.0.0.1:8888/lab?...` URL printed by Jupyter Lab. If you changed `GET_JUPYTER_PORT`, use the same port in the tunnel.

## Practical conventions

- Keep new analysis notebooks under `~/GET_course_work/notebooks` or another work directory.
- If you edit example notebooks inside the Git checkout, clear outputs before committing or sharing.
- Run long fine-tuning and inference jobs with the course wrapper scripts when possible; notebooks are better for inspection and analysis.
- Stop container Jupyter Lab with `Ctrl-C` in the terminal where it is running.
