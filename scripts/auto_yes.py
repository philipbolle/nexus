#!/usr/bin/env python3
"""
Auto-Yes Tool for Claude Code
Automatically presses "yes" to interactive prompts for a limited time.
Works both locally and over SSH (Termius).

Two modes:
1. Command mode: Run a specific command and answer its prompts
2. Daemon mode: Run in background monitoring current terminal (experimental)
"""

import pexpect
import signal
import sys
import time
import re
import argparse
import logging
import shlex
from typing import List, Tuple, Optional
import psutil
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoYes:
    """Main auto-yes controller."""

    def __init__(self, timeout_minutes: int = 15, patterns: Optional[List[Tuple[str, str]]] = None):
        """
        Initialize auto-yes.

        Args:
            timeout_minutes: Timeout in minutes after which tool stops (daemon mode)
            patterns: List of (regex_pattern, response) tuples
        """
        self.timeout_seconds = timeout_minutes * 60
        self.patterns = patterns or self.default_patterns()
        self.child: Optional[pexpect.spawn] = None
        self.running = False
        self.start_time: float = 0

    @staticmethod
    def default_patterns() -> List[Tuple[str, str]]:
        """Return default pattern-response pairs."""
        return [
            (r'\(y/N\)', 'y\n'),          # (y/N) prompts
            (r'\(Y/n\)', 'y\n'),          # (Y/n) prompts
            (r'confirm\?', 'yes\n'),      # confirm?
            (r'Continue\?', 'y\n'),       # Continue?
            (r'yes/no', 'yes\n'),         # yes/no
            (r'press Enter to skip', '\n'),  # press Enter to skip
            (r'\[Y/n\]', 'y\n'),          # [Y/n]
            (r'\[y/N\]', 'y\n'),          # [y/N]
            (r'Are you sure\?', 'yes\n'), # Are you sure?
            (r'Proceed\?', 'y\n'),        # Proceed?
            (r'OK to continue\?', 'y\n'), # OK to continue?
        ]

    def run_command(self, command: str):
        """
        Run a command and automatically answer its prompts.

        Args:
            command: The command to run (will be split with shlex)
        """
        logger.info(f"Running command: {command}")
        logger.info(f"Monitoring for {len(self.patterns)} prompt patterns")

        # Split command
        cmd_args = shlex.split(command)
        if not cmd_args:
            logger.error("Empty command")
            return

        # Spawn the command
        self.child = pexpect.spawn(
            cmd_args[0],
            cmd_args[1:],
            encoding='utf-8',
            timeout=None,  # No timeout for command execution
            maxread=2000,
            echo=False
        )

        self.running = True
        self.start_time = time.time()
        prompts_answered = 0

        try:
            while self.running:
                try:
                    # Look for any of our patterns
                    pattern_list = [pexpect.EOF, pexpect.TIMEOUT] + [p[0] for p in self.patterns]
                    index = self.child.expect(pattern_list, timeout=1)

                    if index == 0:  # EOF
                        logger.info("Command finished")
                        break
                    elif index == 1:  # TIMEOUT
                        continue
                    else:
                        # Pattern matched (index >= 2)
                        pattern_idx = index - 2
                        pattern, response = self.patterns[pattern_idx]
                        logger.info(f"Matched pattern: {pattern} -> sending: {response.strip()}")
                        self.child.send(response)
                        prompts_answered += 1

                except pexpect.EOF:
                    logger.info("Command finished (EOF)")
                    break
                except pexpect.TIMEOUT:
                    # Normal timeout, continue checking
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    break

            # Wait for command to complete
            self.child.wait()

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()

        elapsed = time.time() - self.start_time
        logger.info(f"Command completed. Answered {prompts_answered} prompts in {elapsed:.1f} seconds")
        return self.child.exitstatus

    def start_daemon(self):
        """Start daemon mode monitoring current terminal (experimental)."""
        if self.running:
            logger.warning("Auto-yes is already running")
            return

        logger.info(f"Starting auto-yes daemon (timeout: {self.timeout_seconds//60} minutes)")
        logger.info(f"Monitoring for {len(self.patterns)} prompt patterns")

        # Get current shell from environment or default to bash
        shell = os.environ.get('SHELL', 'bash')

        # Spawn a child process that attaches to current terminal
        self.child = pexpect.spawn(
            shell,
            encoding='utf-8',
            timeout=1,  # Check every second
            maxread=2000,
            echo=False
        )

        # Set up signal handlers for clean exit
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.running = True
        self.start_time = time.time()
        prompts_answered = 0

        try:
            while self.running and (time.time() - self.start_time < self.timeout_seconds):
                try:
                    # Look for any of our patterns
                    pattern_list = [pexpect.TIMEOUT] + [p[0] for p in self.patterns]
                    self.child.expect(pattern_list)

                    if self.child.after != pexpect.TIMEOUT:
                        # Find matching pattern and send response
                        for pattern, response in self.patterns:
                            if re.search(pattern, self.child.after):
                                logger.info(f"Matched pattern: {pattern} -> sending: {response.strip()}")
                                self.child.send(response)
                                prompts_answered += 1
                                break

                except pexpect.EOF:
                    logger.info("Terminal closed")
                    break
                except pexpect.TIMEOUT:
                    # Normal timeout, continue checking
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    break

                # Small sleep to prevent CPU spin
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.cleanup()

        elapsed = time.time() - self.start_time
        logger.info(f"Auto-yes daemon stopped. Answered {prompts_answered} prompts in {elapsed:.1f} seconds")

    def signal_handler(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def cleanup(self):
        """Clean up child process."""
        if self.child and self.child.isalive():
            self.child.close(force=True)
        self.running = False

    def stop(self):
        """Stop the auto-yes tool."""
        self.running = False
        self.cleanup()


def check_already_running() -> bool:
    """Check if auto-yes is already running."""
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip current process
            if proc.pid == current_pid:
                continue

            cmdline = proc.cmdline()
            if cmdline and 'auto_yes.py' in ' '.join(cmdline):
                logger.warning(f"Auto-yes already running (PID: {proc.pid})")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def main():
    parser = argparse.ArgumentParser(description='Auto-Yes Tool for Claude Code')
    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=15,
        help='Timeout in minutes for daemon mode (default: 15)'
    )
    parser.add_argument(
        '--patterns-file',
        type=str,
        help='YAML file with custom patterns (optional)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    # Modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--command', '-c',
        type=str,
        help='Run a command and answer its prompts (command mode)'
    )
    mode_group.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run in daemon mode monitoring current terminal (experimental)'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Default mode is daemon if no command specified (backward compatibility)
    if not args.command and not args.daemon:
        args.daemon = True

    # Load custom patterns if provided
    patterns = None
    if args.patterns_file:
        try:
            import yaml
            with open(args.patterns_file, 'r') as f:
                custom_patterns = yaml.safe_load(f)
                if custom_patterns and 'patterns' in custom_patterns:
                    patterns = [(p['regex'], p['response']) for p in custom_patterns['patterns']]
                    logger.info(f"Loaded {len(patterns)} custom patterns from {args.patterns_file}")
        except Exception as e:
            logger.error(f"Failed to load patterns file: {e}")
            sys.exit(1)

    # Create auto-yes instance
    auto_yes = AutoYes(timeout_minutes=args.timeout, patterns=patterns)

    if args.command:
        # Command mode
        exit_status = auto_yes.run_command(args.command)
        sys.exit(exit_status if exit_status is not None else 0)
    else:
        # Daemon mode
        if check_already_running():
            logger.error("Auto-yes is already running. Exiting.")
            sys.exit(1)
        try:
            auto_yes.start_daemon()
        except Exception as e:
            logger.error(f"Failed to start auto-yes: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()