<p align="center">
  <img src="imgs/vegvisir_banner_large_whitefont.png" height="250px"/>
</p>

Welcome to Vegvisir, an open-source testing framework for QUIC developers and researchers.

Vegvisir's primary goal is to orchestrate client and server communication over various simulated network conditions to collect logs about your experiments and, subsequentially, help you get insights into your applications' behavior. Simulating allows you to identify and resolve issues that may only occur under specific network conditions, improving the reliability and performance of your application. The codebase uses existing network simulation tools; it was tested with tc-netem and NS3 but should also work with other similar simulation tools. While initially intended only to be used for QUIC-based network applications, the experiments you define for Vegvisir can also use other transport-layer protocols.

Vegvisir can capture any logs/output produced from experiments. By default, compatible QUIC-based applications/implementations will create [qlogs](https://datatracker.ietf.org/doc/draft-ietf-quic-qlog-h3-events/), and the network simulations will create pcaps.
With visualization tools such as [qvis](https://qvis.quictools.info/) and [wireshark](https://www.wireshark.org/), you can quickly analyze these logs and gain a deeper understanding of what's happening under the hood of your application.
Whether you're a developer looking to improve the performance of your software or a researcher studying network behavior, Vegvisir is a powerful addition to your toolkit.

# Preview
<img src="imgs/demo.gif" />

# Installation
```
git clone https://github.com/JorisHerbots/vegvisir
cd ./vegvisir
```

You can opt to install required python packages globally
```
pip3 install -r requirements.txt
```

Or you can create a virtual environment (recommended)
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Vegvisir requires you to have at least Python version `>3.7` installed and only works on Linux `x86_64`.

The following dependencies need to be installed system-wide `docker, docker compose, ethtool, sudo, which` for Vegvisir to work correctly. We support docker compose v2. Docker needs to be [accessible without root privileges](https://docs.docker.com/engine/install/linux-postinstall/).

# Usage
You can run Vegvisir from its root folder using the following command: 
```
python -m vegvisir
```
For help on flags use `python -m vegvisir -h`

To start experiments, use
```
python -m vegvisir run -i implementations.json experiment.json
```

Output will automatically be logged in the `logs` folder unless specified otherwise in the provided `experiment` configuration.

# Setting up experiments
Vegvisir is steered through two configurations: the `implementation` configuration and the `experiment` configuration.

The configuration structures below are described using the [Concise Data Definition Language](https://www.rfc-editor.org/rfc/rfc8610).




## Implementations
Contains a list of all implementations and their configurations.

```
Implementations = {
  clients: {
    + ImplementationName: ClientImplementation
  },
  servers: {
    + ImplementationName: ServerImplementation
  },
  shapers: {
    + ImplementationName: ShaperImplementation
  },
}
ImplementationName = text .regex "^[a-zA-Z0-9_-]+$"
```

```
ClientImplementation = {
  ClientType,
  ? parameters: Parameter,
  ? construct : [* CDCommand], ; Commands executed before "command" if the implementation represents a host command
  ? destruct : [* CDCommand], ; Commands executed before "command" if the implementation represents a host command
}
```

```
ClientType = (
  image: text, ; repo/name:tag
  command: text, ; host command
)
```

```
ServerImplementation = {
  ? image: text, ; repo/name:tag
  ? parameters: Parameter,
}
```

```
ShaperImplementation = {
  ? image: text, ; repo/name:tag
  ? parameters: Parameter,
}
```

```
Parameter = {
  * ParameterKey => bool ; True represents root privileges are required
}
ParameterKey = text .regex "\!(?:(?:\{(?P<parameter>(?:[A-Z0-9_-]+))\})"
```

```
CDCommand = {
  ? root_required: bool .default false,
  command: text,
}
```

## Experiments
Contains a single (repeatable) experiment

```
Experiment = {
  clients: [ClientExperiment],
  servers: [ServerExperiment],
  shapers: [ShaperExperiment],
  environment : Environment,
  settings: Settings,
}
```

```
ClientExperiment = {
  name: text .regex "^[a-zA-Z0-9_-]+$", ; must match one of the names from implementations
  ? log_name : text .regex "^[a-zA-Z0-9_-]+$", ; Name used for logging, if the same client is used for multiple experiment permutation (e.g., other arguments), a unique log_name must be provided for all entries
  ? arguments : Arguments,
}
```

```
Arguments = {
  * (text .regex "\!(?:(?:\{(?P<parameter>(?:[A-Z0-9_-]+))\})") => text, ; Matches a parameter of the respective implementation configuration
}
```

```
Environment = {
  name: DefaultEnvironments,
  ? sensors : [SensorConfiguration],
}
```

```
DefaultEnvironments = "webserver-basic", ; Currently only 1 available
```

```
SensorConfiguration = {
  name: AvailableSensors
  * SensorKey => any
}
SensorKey = text, ; Parameter as defined in the sensor python code
```

```
AvailableSensors = "timeout" / "browser-file-watchdog"
```

```
Settings = {
  label: text .regex "^[a-zA-Z0-9_-]+$", ; label in the logging output folder
  ? description : text, ; Currently unused, but optional to describe the setup in the configuration file
  ? playground : bool .default false, ; Currently unused, coming soon
  ? www_dir : text .default "./www", ; Web root path
  ? iterations: int .default 1, ; The number of times the complete permutation needs to be repeated
}
```

# Examples
## `implementation` configuration for all available [QIR](https://github.com/marten-seemann/quic-interop-runner) images
The `tc-netem` shaper in this example is available in the `images/tc-netem` folder. You can build it by navigating to it and performing the following Docker command `docker build -t tc-netem .`
```
{
    "clients": {
		"aioquic": {
			"image": "aiortc/aioquic-qns",
            "parameters": {"REQUESTS": true}
		},
		"quic-go": {
			"image": "martenseemann/quic-go-interop:latest",
            "parameters": {"REQUESTS": true}
		},
		"quicly": {
			"image": "h2oserver/quicly-interop-runner:latest",
            "parameters": {"REQUESTS": true}
		},
		"ngtcp2": {
			"image": "ghcr.io/ngtcp2/ngtcp2-interop:latest",
            "parameters": {"REQUESTS": true}
		},
		"quant": {
			"image": "ntap/quant:interop",
            "parameters": {"REQUESTS": true}
		},
		"mvfst": {
			"image": "lnicco/mvfst-qns:latest",
            "parameters": {"REQUESTS": true}
		},
		"quiche": {
			"image": "cloudflare/quiche-qns:latest",
            "parameters": {"REQUESTS": true}
		},
		"kwik": {
			"image": "peterdoornbosch/kwik_n_flupke-interop",
            "parameters": {"REQUESTS": true}
		},
		"picoquic": {
			"image": "privateoctopus/picoquic:latest",
            "parameters": {"REQUESTS": true}
		},
		"neqo": {
			"image": "neqoquic/neqo-qns:latest",
            "parameters": {"REQUESTS": true}
		},
		"nginx": {
			"image": "nginx/nginx-quic-qns:latest",
            "parameters": {"REQUESTS": true}
		},
		"msquic": {
			"image": "mcr.microsoft.com/msquic/qns:latest",
            "parameters": {"REQUESTS": true}
		},
		"xquic": {
			"image": "kulsk/xquic:latest",
            "parameters": {"REQUESTS": true}
		},
		"lsquic": {
			"image": "litespeedtech/lsquic-qir:latest",
            "parameters": {"REQUESTS": true}
		}
	},

	"shapers": {
		"ns3-quic": {
			"image": "martenseemann/quic-network-simulator",
			"scenarios": {
				"simple-p2p": {
                    "command": "\"simple-p2p --delay=!{LATENCY}ms --bandwidth=!{THROUGHPUT}Mbps --queue=25\"",
                    "parameters": ["THROUGHPUT", "LATENCY"]
				}
			}
		},
		"tc-netem": {
			"image": "tc-netem",
			"scenarios": {
				"simple": {
					"command": "\"simple !{LATENCY} !{THROUGHPUT}\"",
					"parameters": ["THROUGHPUT", "LATENCY"]
				},
				"cellular-loss-good": "\"akamai_cellular_emulation.sh loss_based good\"",
				"cellular-loss-median": "\"akamai_cellular_emulation.sh loss_based median\"",
				"cellular-loss-poor": "\"akamai_cellular_emulation.sh loss_based poor\"",
				"cellular-experience-noloss": "\"akamai_cellular_emulation.sh experience_based noloss\"",
				"cellular-experience-good": "\"akamai_cellular_emulation.sh experience_based good\"",
				"cellular-experience-fair": "\"akamai_cellular_emulation.sh experience_based fair\"",
				"cellular-experience-passable": "\"akamai_cellular_emulation.sh experience_based passable\"",
				"cellular-experience-poor": "\"akamai_cellular_emulation.sh experience_based poor\"",
				"cellular-experience-verypoor": "\"akamai_cellular_emulation.sh experience_based verypoor\""
			}
		}
	},

	"servers": {
		"aioquic": {
			"image": "aiortc/aioquic-qns"
		},
		"quic-go": {
			"image": "martenseemann/quic-go-interop:latest"
		},
		"quicly": {
			"image": "h2oserver/quicly-interop-runner:latest"
		},
		"ngtcp2": {
			"image": "ghcr.io/ngtcp2/ngtcp2-interop:latest"
		},
		"quant": {
			"image": "ntap/quant:interop"
		},
		"mvfst": {
			"image": "lnicco/mvfst-qns:latest"
		},
		"quiche": {
			"image": "cloudflare/quiche-qns:latest"
		},
		"kwik": {
			"image": "peterdoornbosch/kwik_n_flupke-interop"
		},
		"picoquic": {
			"image": "privateoctopus/picoquic:latest"
		},
		"neqo": {
			"image": "neqoquic/neqo-qns:latest"
		},
		"nginx": {
			"image": "nginx/nginx-quic-qns:latest"
		},
		"msquic": {
			"image": "mcr.microsoft.com/msquic/qns:latest"
		},
		"xquic": {
			"image": "kulsk/xquic:latest"
		},
		"lsquic": {
			"image": "litespeedtech/lsquic-qir:latest"
		}
	}
}
```

## `experiment` configuration example
This configuration defines 3 clients, 3 shapers and 3 servers based the implementation configuration above. The experiment execution engine will create 27 test combinations to be run. With the `iterations` value set to two, Vegvisir runs these combinations twice, resulting in a total of 54 test.
```
{
    "clients": [
        {
            "name": "aioquic",
            "arguments": {
                "REQUESTS": "https://!{ORIGIN}/1MB.bin"
            }
        },
        {
            "name": "quic-go",
            "arguments": {
                "REQUESTS": "https://!{ORIGIN}/1MB.bin"
            }
        },
        {
            "name": "ngtcp2",
            "arguments": {
                "REQUESTS": "https://!{ORIGIN}/1MB.bin"
            }
        }
    ],

    "shapers": [
        {
            "name": "tc-netem",
            "log_name": "tc-netem-cellular-loss-median",
            "scenario": "cellular-loss-median"
        },
        {
            "name": "tc-netem",
            "log_name": "tc-netem-cellular-experience-good",
            "scenario": "cellular-experience-good"
        },
        {
            "name": "ns3-quic",
            "scenario": "simple-p2p",
            "arguments": {
                "THROUGHPUT": "30",
                "LATENCY": "10"
            }
        }
    ],
    
    "servers": [
        {"name": "aioquic"},
        {"name": "quic-go"},
        {"name": "ngtcp2"}
    ],

    "environment": {
        "name": "webserver-basic",
        "sensors": [
            {
                "name": "timeout",
                "timeout": 30
            }
        ]
    },

    "settings": {
        "label": "implementation_combinations",
        "www_dir": "./www",
        "iterations": 2
    }
}
``` 

## Minimal example using a browser
This example assumes [google chrome](https://www.google.com/chrome/) is installed and available via `google-chrome-stable`.

`implementation` configuration
```
{
	"clients": {
		"chrome": {
			"parameters": {
				"REQUEST_URL": true
			},
			"command": "google-chrome-stable --origin-to-force-quic-on=!{ORIGIN}:!{ORIGIN_PORT} --enable-experimental-web-platform-features --log-net-log=!{LOG_PATH_CLIENT}/net-log.json --autoplay-policy=no-user-gesture-required --auto-open-devtools-for-tabs --ignore-certificate-errors-spki-list=!{CERT_FINGERPRINT} !{REQUEST_URL}",
			"construct": [
				{
					"root_required": false,
					"command": "python ./util/chrome-set-downloads-folder.py ~/.config/google-chrome/Default/Preferences \"!{DOWNLOAD_PATH_CLIENT}\""
				}
			]
		}
	},

	"shapers": {
		"ns3-quic": {
			"image": "martenseemann/quic-network-simulator",
			"scenarios": {
				"simple-p2p": {
					"command": "\"simple-p2p --delay=!{LATENCY}ms --bandwidth=!{THROUGHPUT}Mbps --queue=25\"",
					"parameters": ["THROUGHPUT", "LATENCY"]
				}
			}
		}
	},

	"servers": {
		"aioquic": {
			"image": "aiortc/aioquic-qns"
		}
	}
}
```

`experiment` configuration
```
{
	"clients": [
		{
			"name": "chrome",
			"arguments": {
				"REQUEST_URL": "https://!{ORIGIN}/1MB.bin"
			}
		}
	],

	"shapers": [
		{
			"name": "ns3-quic",
			"scenario": "simple-p2p",
			"arguments": {
				"THROUGHPUT": "30",
				"LATENCY": "10"
			}
		}
	],
	
	"servers": [
		{"name": "aioquic"}
	],

	"environment": {
		"name": "webserver-basic",
		"sensors": [
			{
				"name": "timeout",
				"timeout": 30
			},
			{
				"name": "browser-file-watchdog",
				"expected_filename": ["1MB.bin"]
			}
		]
	},

	"settings": {
		"label": "browser_download_test",
		"www_dir": "./www",
		"iterations": 1
	}
}
```

# Creating your own images
We use the same method of creating images as used in the [QUIC Interop Runner project](https://github.com/marten-seemann/quic-network-simulator#building-your-own-quic-docker-image). On top of that, we provide our parametric system to dynamically steer your image. You can define parameters in the `implementations` configuration and access them as environment variables within your image scripts. We therefore do not support QIR's `SERVER_PARAMS` and `CLIENT_PARAMS` (unless you define these as parameters).

# Frequently Asked Questions
## Why do I need to enter my sudo password?!
Vegvisir requires root privileges to change system specifics such as routes to assure the experiments run correctly. Additionally, you can use privileged calls in your experiment setups.

## Then why don't you just use polkit?
We created a version of Vegvisir using Polkit. However, since experiments can span multiple days, Polkit would require re-authenticating every once in a while making it impossible to continue without human intervention.

## How secure is Vegvisir?
Vegvisir is intended to be used for research and development. Its experiment execution engine has access to privileged calls. We do not advise making Vegvisir accessible in a public network. :warning: You are responsible for the software being used in Vegvisir, do not run untrusted software or experiments.

## Vegvisir locked my user account?
Wrongly entering your sudo password too many times can trigger a lock, this is unrelated to Vegvisir and default behavior of Linux, use `faillock --reset` to resolve this issue if you still have access to the system.

## Why the name Vegvisir?
We were playing [Valheim](https://www.valheimgame.com/) at the time of creating this repository. Since we did not have a good name, we chose `Vegvisir` for its meaning and it stuck.

> A vegvísir (Icelandic for 'sign post, wayfinder') is an Icelandic magical stave intended to help the bearer find their way through rough weather.

Source: [Wikipedia](https://en.wikipedia.org/wiki/Vegv%C3%ADsir)