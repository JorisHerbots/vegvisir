from dataclasses import dataclass


@dataclass
class ExperimentPaths:
    """
    
    """
    log_path_root: str | None = None
    log_path_date: str | None = None
    log_path_iteration: str | None = None
    log_path_permutation: str | None = None
    log_path_client: str | None = None
    log_path_server: str | None = None
    log_path_shaper: str | None = None

    implementations_configuration_file_path: str | None = None
    experiment_configuration_file_path: str | None = None

    www_path: str | None = None