"""Vyper CLI — Smart Contract Bug Hunter Command Line Interface.

Usage:
    vyper audit <address>          Full audit pipeline
    vyper scan <file>              Quick scan (slither + mythril + echidna)
    vyper exploit <finding-id>     Generate PoC exploit
    vyper status <audit-id>        Check audit status
    vyper list                     List all audits
    vyper up                       Start all Docker services
    vyper down                     Stop all Docker services
    vyper logs [service]           View service logs
    vyper ps                       Show running services
    vyper dashboard                [removed] use 'vyper monitor' instead
    vyper health                   Check all service health
    vyper config                   Show configuration
"""

__version__ = "0.1.0"
__author__ = "Vyper Team"
