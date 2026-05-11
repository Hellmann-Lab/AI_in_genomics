import hydra

from get_model.run_region import run_zarr


@hydra.main(
    config_path="../config",
    version_base="1.3",
)
def main(cfg):
    if "model" not in cfg or "dataset" not in cfg:
        raise ValueError(
            "No training config was loaded. Please pass --config-name, for example: "
            "--config-name own_finetune_tutorial_pbmc"
        )
    run_zarr(cfg)


if __name__ == "__main__":
    main()
