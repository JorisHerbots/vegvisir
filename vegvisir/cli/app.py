import argparse
from datetime import datetime
from getpass import getpass
import logging
import math
import random
import shutil
import signal
import sys
import threading
import time

import colour

from .. import runner

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
    version = "V2.0.0-dev"  # TODO jherbots fill in with version number from better location 
    banner_width = 38  # characters
    pre_padding = math.floor(banner_width * 3 / 4) - math.floor(len(version)/2)
    version_string = " " * pre_padding + version + " " * (banner_width - pre_padding - len(version)) + "\n"
    
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

def main():
    global tui_start_timestamp, tui_client_name, tui_shaper_name, tui_server_name, tui_progress_current, tui_progress_total, tui_threads_run

    argument_parser = argparse.ArgumentParser(prog="vegvisir", description=generate_banner(), formatter_class=argparse.RawTextHelpFormatter)
    argument_parser.add_argument("-i", "--implementations", dest="implementations_path", metavar="implementations.json", default="./implementations.json")
    argument_parser.add_argument("-e", "--experiment", dest="experiment_path", metavar="experiment.json", default="./experiment.json")
    argument_parser.add_argument("-v", "--verbose", action="count", default=0)
    argument_parser.add_argument("--version", action="version", version="TODO")
    vegvisir_arguments = argument_parser.parse_args()

    implementations_path = vegvisir_arguments.implementations_path
    experiment_path = vegvisir_arguments.experiment_path

    flush_print((
        f"{control_sequences['ERASE_ALL']}"
        f"{control_sequences['SET_CURSOR_POSITION'].format(column=1, row=1)}"
    ))
    construct_tui()
    signal.signal(signal.SIGWINCH, calculate_and_set_screen_size)
    signal.signal(signal.SIGINT, sigint_handler)
    print(generate_banner())
    
    sudo_pass = getpass("Enter password to run sudo commands: ")
    
    tui_start_timestamp = datetime.now()
    tui_thread = threading.Thread(target=tui_render_tick)
    tui_thread.start()
    
    try:
        r = runner.Runner(sudo_password=sudo_pass, debug=True, implementations_file_path=implementations_path)
        r.load_experiment_from_file(experiment_path)
        # r.load_experiment_from_file("test_run2.json")
        # r.load_experiment_from_file("test_run.json")
        for experiment in r.run():
            tui_client_name, tui_shaper_name, tui_server_name, tui_progress_current, tui_progress_total = experiment
    except runner.VegvisirInvalidImplementationConfigurationException as e:
        logging.error("Vegvisir implementations configuration contains incorrect data, halting execution")
        logging.error(e)
        destruct_tui()
        sys.exit(1)
    except runner.VegvisirInvalidExperimentConfigurationException as e:
        logging.error("Vegvisir experiment configuration contains incorrect data, halting execution")
        logging.error(e)
        destruct_tui()
        sys.exit(1)
    except runner.VegvisirArgumentException as e:
        logging.error("Vegvisir implementations or experiment configuration contains a wrongfully configured argument, halting execution")
        logging.error(e)
        destruct_tui()
        sys.exit(1)
    except (runner.VegvisirException, Exception) as e:  # Exception allows for clean shutdowns of the GUI
        logging.error("Generic Vegvisir error encountered, halting exception.")
        logging.error(e)
        destruct_tui()
        sys.exit(1)

    destruct_tui()
    print(f"Vegvisir run finished. Total elapsed time {datetime.now()-tui_start_timestamp}")