import argparse
import logging
import math
import random
import shutil
import signal
import sys
import threading
import time
from datetime import datetime
from getpass import getpass

import colour

from vegvisir.configuration import Configuration
from vegvisir.housekeeping import (freeze_implementations_configuration, load_frozen_implementations)

from .. import __version__ as vegvisir_version
from .. import exceptions, runner

# Globals
'''
CSI Ps ; Ps r
        Set Scrolling Region [top;bottom] (default = full size of
        window) (DECSTBM), VT100.

ESC 7     Save Cursor (DECSC), VT100.

ESC 8     Restore Cursor (DECRC), VT100.

CSI Ps ; Ps H
        Cursor Position [row;column] (default = [1,1]) (CUP).
https://vt100.net/docs/vt510-rm/HVP.html

CSI Ps A  Cursor Up Ps Times (default = 1) (CUU).


CSI ? Ps K
          Erase in Line (DECSEL), VT220.
            Ps = 0  ⇒  Selective Erase to Right (default).
            Ps = 1  ⇒  Selective Erase to Left.
            Ps = 2  ⇒  Selective Erase All.
'''
control_sequences = {
    "SET_SCROLL_REGION": "\x1B[{top};{bottom}r",  # 1-indexed
    "SAVE_CURSOR": "\x1B7",
    "RESTORE_CURSOR": "\x1B8",
    "SET_CURSOR_POSITION": "\x1B[{row};{column}H",
    "SHIFT_CURSOR_UP": "\x1B[{lines}A",
    "ERASE_TO_RIGHT": "\x1B[0K",
    "ERASE_ALL": "\x1B[2J",
    "BOLD": "\x1B[1m",
    "COLOR": "\x1B[38;2;{r};{g};{b}m",
    "CLEAR_COLOR": "\x1B[0m",
}
tui_columns, tui_lines = shutil.get_terminal_size()
tui_tick_counter = 0  # Used and controlled by tui animations
tui_start_timestamp = None  # Controlled by the main method, used as a postfix in the progressbar
tui_client_name = tui_shaper_name = tui_server_name = "unknown"
tui_progress_current = 0
tui_progress_total = 0
tui_threads_run = True
tui_tick_delta_sec = 0.08

class VegvisirLogHandler(logging.StreamHandler):
    def __init__(self):
        super(VegvisirLogHandler, self).__init__()

    def emit(self, record):
        if type(record.msg) is not str or "\n" not in record.msg:
            super(VegvisirLogHandler, self).emit(record)
        else:    
            messages = record.msg.split("\n")
            for msg in messages:
                record.msg = msg
                super(VegvisirLogHandler, self).emit(record)

def configure_logging():
    logging.addLevelName(logging.DEBUG, f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=211, g=215, b=207)}Debug >{control_sequences['CLEAR_COLOR']}")
    # logging.addLevelName(logging.INFO, f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=6, g=152, b=154)}Info >{control_sequences['CLEAR_COLOR']}")
    logging.addLevelName(logging.INFO, f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=78, g=154, b=6)}Info >{control_sequences['CLEAR_COLOR']}")
    logging.addLevelName(logging.WARNING, f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=196, g=160, b=0)}Warning >{control_sequences['CLEAR_COLOR']}")
    logging.addLevelName(logging.ERROR, f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=204, g=0, b=0)}Error >{control_sequences['CLEAR_COLOR']}")
    logging.addLevelName(logging.CRITICAL, f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=204, g=0, b=0)}Critical >{control_sequences['CLEAR_COLOR']}")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    console_handler = VegvisirLogHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    return logger, console_handler
logger, console_handler = configure_logging()

def flush_print(s):
    sys.stdout.write(s)
    sys.stdout.flush()

def construct_tui():
    flush_print((
        f"{control_sequences['SAVE_CURSOR']}"
        f"{control_sequences['SET_SCROLL_REGION'].format(top=1, bottom=tui_lines-1)}"
        f"{control_sequences['RESTORE_CURSOR']}"
        f"{control_sequences['SHIFT_CURSOR_UP'].format(lines=1)}"
        f"{control_sequences['ERASE_TO_RIGHT']}"
    ))

def destruct_tui():
    global tui_threads_run
    if tui_threads_run:
        tui_threads_run = False  # In case this was not done yet
        time.sleep(0.2)
    flush_print((
        f"{control_sequences['SAVE_CURSOR']}"
        f"{control_sequences['SET_SCROLL_REGION'].format(top=1, bottom=tui_lines)}"
        f"{control_sequences['SET_CURSOR_POSITION'].format(row=tui_lines, column=0)}"
        f"{control_sequences['ERASE_TO_RIGHT']}"
        f"{control_sequences['RESTORE_CURSOR']}"
    ))

def sigint_handler(signal_number, stack_frame):
    global tui_threads_run
    tui_threads_run = False
    time.sleep(0.3)
    destruct_tui()
    raise KeyboardInterrupt

def calculate_and_set_screen_size(signal_number, stack_frame):
    global tui_columns, tui_lines
    tui_columns, tui_lines = shutil.get_terminal_size()
    construct_tui()

def generate_banner(fancy_print=True):
    banner_width = 38  # characters
    pre_padding = math.floor(banner_width * 3 / 4) - math.floor(len(vegvisir_version)/2)
    version_string = " " * pre_padding + vegvisir_version + " " * (banner_width - pre_padding - len(vegvisir_version)) + "\n"
    
    banner = (
        " __     __               _     _      " + "\n"
        " \ \   / /__  __ ___   _(_)___(_)_ __ " + "\n"
        "  \ \ / / _ \/ _` \ \ / / / __| | '__|" + "\n"
        "   \ V /  __/ (_| |\ V /| \__ \ | |   " + "\n"
        "    \_/ \___|\__, | \_/ |_|___/_|_|   " + "\n"
        "             |___/                    " + "\n"
        f"{version_string}" + "\n"
    )

    if not fancy_print:
        return banner

    gradients = [
        ("#f43b47", "#453a94"),
        ("#9796f0", "#fbc7d4"),
        ("#C33764", "#1D2671"),
    ]
    gradient_pick = random.choice(gradients)
    banner_split = banner.splitlines()
    fancy_banner = ""
    for line, color in zip(banner_split, colour.Color(gradient_pick[0]).range_to(gradient_pick[1], len(banner_split))):
        fancy_banner += (f"{control_sequences['COLOR'].format(r=math.floor(color.red * 255), g=math.floor(color.green * 255), b=math.floor(color.blue * 255))}{line}\n")
    fancy_banner += control_sequences["CLEAR_COLOR"]
    return fancy_banner

def generate_progress_bar():
    loading_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    packet_char = (
            "    ",
            "    ",
			"▫   ",
			"▫▫  ",
			"▫▫▫ ",
			" ▫▫▫",
			"  ▫▫",
			"   ▫",
			"    ",
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
			"   ▫",
			"  ▫▫",
			" ▫▫▫",
			"▫▫▫ ",
			"▫▫  ",
			"▫   ",
    )

    packet_char2 = (
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
            "    ",
			"▫   ",
			"▫▫  ",
			"▫▫▫ ",
			" ▫▫▫",
			"  ▫▫",
			"   ▫",
			"    ",
            "    ",
			"   ▫",
			"  ▫▫",
			" ▫▫▫",
			"▫▫▫ ",
			"▫▫  ",
			"▫   ",
            "    ",
            "    ",
            "    ",
            "    ",
    )

    postfix_info_string = f" Total elapsed time {datetime.now() - tui_start_timestamp}"

    if not all([tui_client_name, tui_shaper_name, tui_server_name]):
        # Happens when no experiment is being run
        return loading_chars[tui_tick_counter % len(loading_chars)] + " Vegvisir is cleaning up -" + postfix_info_string
        
    prefix_info_string = (
        f"[{tui_client_name}]{packet_char[tui_tick_counter % len(packet_char)]}"
        f"[{tui_shaper_name}]{packet_char2[tui_tick_counter % len(packet_char2)]}"
        f"[{tui_server_name}] "
    )
    if tui_progress_total > 1:
        progress = tui_progress_current / tui_progress_total
        infix_info_string = f"{math.floor(progress * 100)}%"
        bar_max_width = tui_columns - 3 - len(prefix_info_string) - len(infix_info_string) - len(postfix_info_string)
        progress_width = math.floor(bar_max_width * progress)
        remainder_width = bar_max_width - progress_width
        return prefix_info_string + infix_info_string + "[" + ("=" * progress_width) + ">" + ("." * remainder_width) + "]" + postfix_info_string
    return prefix_info_string + postfix_info_string

def tui_render_tick():
    global tui_tick_counter
    while tui_threads_run:
        try:
            flush_print((
                f"{control_sequences['SAVE_CURSOR']}"
                f"{control_sequences['SET_CURSOR_POSITION'].format(row=tui_lines, column=0)}"
                f"{control_sequences['ERASE_TO_RIGHT']}"
                f"{generate_progress_bar()}"
                f"{control_sequences['RESTORE_CURSOR']}"
            ))
            tui_tick_counter += 1
        except OverflowError:
            tui_tick_counter = 0
        time.sleep(tui_tick_delta_sec)

def run(vegvisir_arguments):
    global tui_start_timestamp, tui_client_name, tui_shaper_name, tui_server_name, tui_progress_current, tui_progress_total, tui_threads_run

    implementations_path = vegvisir_arguments.implementations
    experiment_path = vegvisir_arguments.experiment

    flush_print((
        f"{control_sequences['ERASE_ALL']}"
        f"{control_sequences['SET_CURSOR_POSITION'].format(column=1, row=1)}"
    ))
    construct_tui()
    signal.signal(signal.SIGWINCH, calculate_and_set_screen_size)
    signal.signal(signal.SIGINT, sigint_handler)
    print(generate_banner())
    
    sudo_pass = getpass(f"{control_sequences['BOLD']}{control_sequences['COLOR'].format(r=211, g=215, b=207)}Vegvisir >{control_sequences['CLEAR_COLOR']} Enter password to run sudo commands: ")
    
    tui_start_timestamp = datetime.now()
    tui_thread = threading.Thread(target=tui_render_tick)
    tui_thread.start()
    
    try:
        configuration = Configuration(implementations_path, experiment_path)
        r = runner.Experiment(sudo_password=sudo_pass, configuration_object=configuration)
        for experiment in r.run():
            tui_client_name, tui_shaper_name, tui_server_name, tui_progress_current, tui_progress_total = experiment
    except exceptions.VegvisirConfigurationException as e:
        logger.error("Vegvisir generic configuration error, halting execution")
        logger.error(e)
        destruct_tui()
        sys.exit(1)
    except exceptions.VegvisirInvalidImplementationConfigurationException as e:
        logger.error("Vegvisir implementations configuration contains incorrect data, halting execution")
        logger.error(e)
        destruct_tui()
        sys.exit(1)
    except exceptions.VegvisirInvalidExperimentConfigurationException as e:
        logger.error("Vegvisir experiment configuration contains incorrect data, halting execution")
        logger.error(e)
        destruct_tui()
        sys.exit(1)
    except exceptions.VegvisirArgumentException as e:
        logger.error("Vegvisir implementations or experiment configuration contains a wrongfully configured argument, halting execution")
        logger.error(e)
        destruct_tui()
        sys.exit(1)
    except (exceptions.VegvisirException, Exception) as e:  # Exception allows for clean shutdowns of the GUI
        logger.error("Generic Vegvisir error encountered, halting exception.")
        logger.error(e)
        destruct_tui()
        sys.exit(1)

    destruct_tui()
    logger.info(f"Vegvisir experiment finished. Total elapsed time {datetime.now()-tui_start_timestamp}")

def freeze(vegvisir_arguments):
    print(generate_banner())
    implementations_file = vegvisir_arguments.implementations
    try:
        config = Configuration(implementations_path=implementations_file)
        logger.info(f"Starting freeze of implementations file [{implementations_file}]")
        freeze_implementations_configuration(config)
        logger.info("Successfully archived the provided implementations configuration. You can now import it onto another system.")
    except exceptions.VegvisirConfigurationException as e:
        logger.error("Vegvisir generic configuration error, halting execution")
        logger.error(e)
        sys.exit(1)
    except exceptions.VegvisirInvalidImplementationConfigurationException as e:
        logger.error("Vegvisir implementations configuration contains incorrect data, halting execution")
        logger.error(e)
        sys.exit(1)
    except exceptions.VegvisirFreezeException as e:
        logger.error("Freezing of implementations configuration failed, halting execution")
        logger.error(e)
        sys.exit(1)

def load(vegvisir_arguments):
    print(generate_banner())
    try:
        logger.info(f"Starting load of archive [{vegvisir_arguments.archive}]")
        load_frozen_implementations(vegvisir_arguments.archive)
        logger.info(f"Successfully loaded the provided archive. You can now utilize the implementation contained in it.")
    except exceptions.VegvisirFreezeException as e:
        logging.error(e)

class SubcommandHelpFormatter(argparse.RawDescriptionHelpFormatter):
    # https://stackoverflow.com/a/13429281
    # Removes the metavar help line for an overall cleaner experience
    def _format_action(self, action):
        parts = super(argparse.RawDescriptionHelpFormatter, self)._format_action(action)
        if action.nargs == argparse.PARSER:
            parts = "\n".join(parts.split("\n")[1:])
        return parts

def main():
    argument_parser = argparse.ArgumentParser(prog="vegvisir", description=generate_banner(), formatter_class=SubcommandHelpFormatter)
    argument_parser.add_argument("-V", "--version", action="version", version=f"Vegvisir V{vegvisir_version}")
    argument_parser.add_argument("-v", "--verbose", action="store_true", help="Enable additional debug logs to be printed to the commandline")
    argument_subparsers = argument_parser.add_subparsers(title="Commands", metavar="[COMMAND]", dest="command")

    experiment_parser = argument_subparsers.add_parser("run", aliases=["r"], help="Run an experiment using Vegvisir", description=generate_banner(), formatter_class=argparse.RawTextHelpFormatter)
    experiment_parser.add_argument("-i", "--implementations",  dest="implementations", metavar="[IMPLEMENTATIONS FILE]", help="Defaults to ./implementations.json", default="./implementations.json")
    experiment_parser.add_argument("-q", "--quiet", action="store_true", help="Only print critical warnings and errors. Logs will still be saved to the log directory.")
    experiment_parser.add_argument("experiment", metavar="[EXPERIMENT FILE]", default="./experiment.json")

    freeze_parser = argument_subparsers.add_parser("freeze", aliases=["f"], help="Freeze a set of docker images defined in the provided implementations file using docker save", description=generate_banner(), formatter_class=argparse.RawTextHelpFormatter)
    freeze_parser.add_argument("-i", "--implementations",  dest="implementations", metavar="[IMPLEMENTATIONS FILE]", help="Defaults to ./implementations.json", default="./implementations.json")
    # freeze_parser.add_argument("out", metavar="OUT", help="Filename for the frozen archive")

    load_parser = argument_subparsers.add_parser("load", aliases=["l"], help="Load a frozen archive", description=generate_banner(), formatter_class=argparse.RawTextHelpFormatter)
    load_parser.add_argument("archive", metavar="[ARCHIVE FILE]")

    vegvisir_arguments = argument_parser.parse_args()
    if vegvisir_arguments.verbose:
        console_handler.setLevel(logging.DEBUG)
        logger.debug("Verbose output requested. Console logger set to debug-level.")
    
    command_to_callback_map = {
        "r": run,
        "f": freeze,
        "l": load,
        "run": run,
        "freeze": freeze,
        "load": load,
    }

    command_callback = command_to_callback_map.get(vegvisir_arguments.command, None)
    if command_callback:
        command_callback(vegvisir_arguments)
    else:
        argument_parser.print_help()
