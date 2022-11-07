from vegvisir.environments import webserver, sensors

default_environment = "webserver-basic"
available_environments = {
    "webserver-basic": webserver.WebserverBasic
}

available_sensors = {
    "timeout": sensors.TimeoutSensor,
    "file-watchdog": sensors.FileWatchdogSensor
}