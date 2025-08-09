
"""This module implements a PacketAnalyzer class using scapy"""

import ipaddress
from collections import Counter
import scapy.all as scapy


class PacketAnalyzer:
    """
    A class for analyzing network packets from a pcap file using Scapy.
    Supports filtering by source/destination IP and port, and provides
    statistics such as protocol counts and top IP addresses.
    """

    def __init__(self, pcap_path: str) -> None:
        """
        Initialize the analyzer with the path to a pcap file.

        Parameters:
            pcap_path (str): Path to the pcap file.
        """
        self.pcap_path = pcap_path

    def analyze(
        self,
        src_ip: str = None,
        dst_ip: str = None,
        src_port: int = None,
        dst_port: int = None
    ) -> dict:
        """
        Analyze packets from the pcap file based on given filters.

        Parameters:
            src_ip (str, optional): Source IP address to filter.
            dst_ip (str, optional): Destination IP address to filter.
            src_port (int, optional): Source port number to filter.
            dst_port (int, optional): Destination port number to filter.

        Returns:
            dict: A dictionary containing packet statistics.
        """
        try:
            packets = scapy.rdpcap(self.pcap_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"The file {self.pcap_path} was not found."
            ) from e
        except Exception as e:
            raise OSError(
                f"Error reading the pcap file: {e}"
            ) from e

        # Validate IP addresses, if provided
        if src_ip:
            self._validate_ip(src_ip, "source")
        if dst_ip:
            self._validate_ip(dst_ip, "destination")

        protocol_counts = Counter()
        src_ip_counter = Counter()
        dst_ip_counter = Counter()
        total_packets = 0

        for packet in packets:
            if not self._packet_matches(
                packet, src_ip, dst_ip, src_port, dst_port
            ):
                continue

            if not packet.haslayer(scapy.IP):
                continue

            total_packets += 1
            ip_layer = packet[scapy.IP]

            if packet.haslayer(scapy.TCP):
                protocol_counts["TCP"] += 1
            elif packet.haslayer(scapy.UDP):
                protocol_counts["UDP"] += 1
            elif packet.haslayer(scapy.ICMP):
                protocol_counts["ICMP"] += 1
            else:
                protocol_counts["Others"] += 1

            src_ip_counter[ip_layer.src] += 1
            dst_ip_counter[ip_layer.dst] += 1

        result = {
            "total_packets": total_packets,
            "protocol_counts": dict(protocol_counts),
            "top_source_ips": src_ip_counter.most_common(5),
            "top_destination_ips": dst_ip_counter.most_common(5)
        }

        return result

    def _packet_matches(
        self,
        packet,
        src_ip: str,
        dst_ip: str,
        src_port: int,
        dst_port: int
    ) -> bool:
        """
        Check if a packet matches the specified IP and port filters.

        Parameters:
            packet: Scapy packet object.
            src_ip (str): Source IP address filter.
            dst_ip (str): Destination IP address filter.
            src_port (int): Source port number filter.
            dst_port (int): Destination port number filter.

        Returns:
            bool: True if the packet matches all filters, else False.
        """
        if src_ip:
            if not packet.haslayer(scapy.IP):
                return False
            if packet[scapy.IP].src != src_ip:
                return False

        if dst_ip:
            if not packet.haslayer(scapy.IP):
                return False
            if packet[scapy.IP].dst != dst_ip:
                return False

        if src_port:
            if packet.haslayer(scapy.TCP):
                if packet[scapy.TCP].sport != src_port:
                    return False
            elif packet.haslayer(scapy.UDP):
                if packet[scapy.UDP].sport != src_port:
                    return False
            else:
                return False

        if dst_port:
            if packet.haslayer(scapy.TCP):
                if packet[scapy.TCP].dport != dst_port:
                    return False
            elif packet.haslayer(scapy.UDP):
                if packet[scapy.UDP].dport != dst_port:
                    return False
            else:
                return False

        return True

    def _validate_ip(self, ip_str: str, label: str) -> None:
        """
        Validate an IPv4 address string.

        Parameters:
            ip_str (str): The IP address to validate.
            label (str): Label to indicate whether it's source or destination.

        Raises:
            ValueError: If the IP address is invalid.
        """
        try:
            ipaddress.ip_address(ip_str)
        except ValueError as e:
            raise ValueError(f"Invalid {label} IP address: {ip_str}") from e

