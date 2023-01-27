from dataclasses import dataclass
import dataclasses
from typing import Dict


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

    download_path_client: str | None = None

    implementations_configuration_file_path: str | None = None
    experiment_configuration_file_path: str | None = None

    www_path: str | None = None


@dataclass
class VegvisirArguments:
    """
    Collection of arguments provided by Vegvisir

    """

    # CLIENT: str | None = None
    # SERVER: str | None = None
    # SHAPER: str | None = None
    
    # CERTS: str | None = None
    # WWW: str | None = None
    # DOWNLOADS: str | None = None

    ROLE : str | None = None

    LOG_PATH_CLIENT: str | None = None
    LOG_PATH_SERVER: str | None = None
    LOG_PATH_SHAPER: str | None = None
    DOWNLOAD_PATH_CLIENT: str | None = None

    ORIGIN: str | None = None
    ORIGIN_IPV4: str | None = None
    ORIGIN_IPV6: str | None = None
    ORIGIN_PORT: str | None = None

    CERT_FINGERPRINT: str | None = None
    QLOGDIR : str | None = None
    SSLKEYLOGFILE : str | None = None
    WAITFORSERVER: str | None = None

    SCENARIO: str | None = None
    ENVIRONMENT : str | None = None
    TESTCASE : str | None = None

    def dict(self) -> Dict[str, str]:
        return {key: value for key, value in dataclasses.asdict(self).items() if value is not None}
    
    def dummy(self) -> Dict[str, str]:
        return {key: "dummyData" for key in dataclasses.asdict(self)}