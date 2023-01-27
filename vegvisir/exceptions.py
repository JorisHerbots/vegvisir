class VegvisirException(Exception):
	pass

class VegvisirConfigurationException(VegvisirException):
    pass

class VegvisirInvalidImplementationConfigurationException(VegvisirException):
	pass

class VegvisirInvalidExperimentConfigurationException(VegvisirException):
	pass

class VegvisirCommandExecutionException(VegvisirException):
	pass

class VegvisirRunFailedException(VegvisirException):
	pass

###

class VegvisirParameterException(VegvisirException):
	pass

class VegvisirArgumentException(VegvisirException):
	pass

class VegvisirCommandException(VegvisirException):
	pass


###

class VegvisirFreezeException(VegvisirException):
    pass