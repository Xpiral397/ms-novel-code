# tests

"""Unit tests for PacketAnalyzer class."""

import unittest
from unittest.mock import patch, MagicMock
from main import PacketAnalyzer


class TestPacketAnalyzer(unittest.TestCase):
    """Test cases for PacketAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_pcap_path = "test_traffic.pcap"
        self.analyzer = PacketAnalyzer(self.valid_pcap_path)

    def test_init_valid_path(self):
        """Test initialization with valid pcap path."""
        analyzer = PacketAnalyzer("valid_path.pcap")
        self.assertEqual(analyzer.pcap_path, "valid_path.pcap")

    def test_init_empty_path(self):
        """Test initialization with empty path."""
        analyzer = PacketAnalyzer("")
        self.assertEqual(analyzer.pcap_path, "")

    @patch('main.scapy.rdpcap')
    def test_analyze_file_not_found(self, mock_rdpcap):
        """Test analyze method with non-existent pcap file."""
        mock_rdpcap.side_effect = FileNotFoundError("File not found")

        with self.assertRaises(FileNotFoundError) as context:
            self.analyzer.analyze()

        self.assertIn("was not found", str(context.exception))

    @patch('main.scapy.rdpcap')
    def test_analyze_file_read_error(self, mock_rdpcap):
        """Test analyze method with file read error."""
        mock_rdpcap.side_effect = Exception("Read error")

        with self.assertRaises(OSError) as context:
            self.analyzer.analyze()

        self.assertIn("Error reading the pcap file", str(context.exception))

    @patch('main.scapy.rdpcap')
    def test_analyze_empty_pcap_file(self, mock_rdpcap):
        """Test analyze with empty pcap file."""
        mock_rdpcap.return_value = []

        result = self.analyzer.analyze()

        expected = {
            "total_packets": 0,
            "protocol_counts": {},
            "top_source_ips": [],
            "top_destination_ips": []
        }
        self.assertEqual(result, expected)

    @patch('main.scapy.rdpcap')
    def test_analyze_no_ip_layer_packets(self, mock_rdpcap):
        """Test analyze with packets having no IP layer."""
        mock_packet = MagicMock()
        mock_packet.haslayer.return_value = False
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze()

        expected = {
            "total_packets": 0,
            "protocol_counts": {},
            "top_source_ips": [],
            "top_destination_ips": []
        }
        self.assertEqual(result, expected)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_analyze_tcp_packets(self, mock_tcp, mock_ip, mock_rdpcap):
        """Test analyze with TCP packets."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_tcp
        ]
        mock_packet.__getitem__.return_value.src = "192.168.1.1"
        mock_packet.__getitem__.return_value.dst = "192.168.1.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze()

        self.assertEqual(result["total_packets"], 1)
        self.assertEqual(result["protocol_counts"]["TCP"], 1)
        self.assertEqual(result["top_source_ips"][0], ("192.168.1.1", 1))
        self.assertEqual(result["top_destination_ips"][0], ("192.168.1.2", 1))

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.UDP')
    def test_analyze_udp_packets(self, mock_udp, mock_ip, mock_rdpcap):
        """Test analyze with UDP packets."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_udp
        ]
        mock_packet.__getitem__.return_value.src = "10.0.0.1"
        mock_packet.__getitem__.return_value.dst = "10.0.0.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze()

        self.assertEqual(result["total_packets"], 1)
        self.assertEqual(result["protocol_counts"]["UDP"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.ICMP')
    def test_analyze_icmp_packets(self, mock_icmp, mock_ip, mock_rdpcap):
        """Test analyze with ICMP packets."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_icmp
        ]
        mock_packet.__getitem__.return_value.src = "8.8.8.8"
        mock_packet.__getitem__.return_value.dst = "192.168.1.1"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze()

        self.assertEqual(result["total_packets"], 1)
        self.assertEqual(result["protocol_counts"]["ICMP"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    def test_analyze_other_protocol_packets(self, mock_ip, mock_rdpcap):
        """Test analyze with other protocol packets."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer == mock_ip
        mock_packet.__getitem__.return_value.src = "172.16.0.1"
        mock_packet.__getitem__.return_value.dst = "172.16.0.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze()

        self.assertEqual(result["total_packets"], 1)
        self.assertEqual(result["protocol_counts"]["Others"], 1)

    def test_validate_ip_valid_ipv4(self):
        """Test IP validation with valid IPv4 addresses."""
        # Should not raise any exception
        self.analyzer._validate_ip("192.168.1.1", "source")
        self.analyzer._validate_ip("0.0.0.0", "destination")
        self.analyzer._validate_ip("255.255.255.255", "test")

    def test_validate_ip_invalid_ipv4(self):
        """Test IP validation with invalid IPv4 addresses."""
        with self.assertRaises(ValueError) as context:
            self.analyzer._validate_ip("256.1.1.1", "source")
        self.assertIn("Invalid source IP address", str(context.exception))

        with self.assertRaises(ValueError):
            self.analyzer._validate_ip("192.168.1", "destination")

        with self.assertRaises(ValueError):
            self.analyzer._validate_ip("not.an.ip", "test")

    @patch('main.scapy.rdpcap')
    def test_analyze_with_invalid_src_ip(self, mock_rdpcap):
        """Test analyze with invalid source IP filter."""
        mock_rdpcap.return_value = []

        with self.assertRaises(ValueError) as context:
            self.analyzer.analyze(src_ip="invalid.ip")
        self.assertIn("Invalid source IP address", str(context.exception))

    @patch('main.scapy.rdpcap')
    def test_analyze_with_invalid_dst_ip(self, mock_rdpcap):
        """Test analyze with invalid destination IP filter."""
        mock_rdpcap.return_value = []

        with self.assertRaises(ValueError) as context:
            self.analyzer.analyze(dst_ip="999.999.999.999")
        self.assertIn("Invalid destination IP address",
                      str(context.exception))

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_packet_matches_src_ip_filter(self, mock_tcp, mock_ip,
                                          mock_rdpcap):
        """Test packet filtering by source IP."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_tcp
        ]
        mock_packet.__getitem__.return_value.src = "192.168.1.1"
        mock_packet.__getitem__.return_value.dst = "192.168.1.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(src_ip="192.168.1.1")

        self.assertEqual(result["total_packets"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_packet_matches_dst_ip_filter(self, mock_tcp, mock_ip,
                                          mock_rdpcap):
        """Test packet filtering by destination IP."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_tcp
        ]
        mock_packet.__getitem__.return_value.src = "192.168.1.1"
        mock_packet.__getitem__.return_value.dst = "192.168.1.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(dst_ip="192.168.1.2")

        self.assertEqual(result["total_packets"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_packet_matches_src_port_tcp_filter(self, mock_tcp, mock_ip,
                                                mock_rdpcap):
        """Test packet filtering by TCP source port."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_tcp
        ]
        mock_packet.__getitem__.side_effect = lambda layer: (
            MagicMock(src="192.168.1.1", dst="192.168.1.2")
            if layer == mock_ip
            else MagicMock(sport=80, dport=443)
        )
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(src_port=80)

        self.assertEqual(result["total_packets"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.UDP')
    def test_packet_matches_dst_port_udp_filter(self, mock_udp, mock_ip,
                                                mock_rdpcap):
        """Test packet filtering by UDP destination port."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_udp
        ]
        mock_packet.__getitem__.side_effect = lambda layer: (
            MagicMock(src="10.0.0.1", dst="10.0.0.2")
            if layer == mock_ip
            else MagicMock(sport=53, dport=53)
        )
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(dst_port=53)

        self.assertEqual(result["total_packets"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    def test_packet_no_match_port_filter_no_tcp_udp(self, mock_ip,
                                                    mock_rdpcap):
        """Test port filter with non-TCP/UDP packets."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer == mock_ip
        mock_packet.__getitem__.return_value.src = "192.168.1.1"
        mock_packet.__getitem__.return_value.dst = "192.168.1.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(src_port=80)

        self.assertEqual(result["total_packets"], 0)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_analyze_multiple_filters_combined(self, mock_tcp, mock_ip,
                                               mock_rdpcap):
        """Test analyze with multiple filters combined."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_tcp
        ]
        mock_packet.__getitem__.side_effect = lambda layer: (
            MagicMock(src="192.168.1.100", dst="8.8.8.8")
            if layer == mock_ip
            else MagicMock(sport=12345, dport=80)
        )
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(
            src_ip="192.168.1.100",
            dst_ip="8.8.8.8",
            src_port=12345,
            dst_port=80
        )

        self.assertEqual(result["total_packets"], 1)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_analyze_no_packets_match_filters(self, mock_tcp, mock_ip,
                                              mock_rdpcap):
        """Test analyze when no packets match the filters."""
        mock_packet = MagicMock()
        mock_packet.haslayer.side_effect = lambda layer: layer in [
            mock_ip, mock_tcp
        ]
        mock_packet.__getitem__.return_value.src = "192.168.1.1"
        mock_packet.__getitem__.return_value.dst = "192.168.1.2"
        mock_rdpcap.return_value = [mock_packet]

        result = self.analyzer.analyze(src_ip="10.0.0.1")

        expected = {
            "total_packets": 0,
            "protocol_counts": {},
            "top_source_ips": [],
            "top_destination_ips": []
        }
        self.assertEqual(result, expected)

    @patch('main.scapy.rdpcap')
    @patch('main.scapy.IP')
    @patch('main.scapy.TCP')
    def test_analyze_top_ips_ordering(self, mock_tcp, mock_ip, mock_rdpcap):
        """Test top IPs are correctly ordered by frequency."""
        packets = []
        ips = [
            ("192.168.1.1", "8.8.8.8", 3),  # src, dst, count
            ("192.168.1.2", "8.8.4.4", 5),
            ("192.168.1.3", "1.1.1.1", 1),
        ]

        for src_ip, dst_ip, count in ips:
            for _ in range(count):
                mock_packet = MagicMock()
                mock_packet.haslayer.side_effect = lambda layer: layer in [
                    mock_ip, mock_tcp
                ]
                mock_packet.__getitem__.return_value.src = src_ip
                mock_packet.__getitem__.return_value.dst = dst_ip
                packets.append(mock_packet)

        mock_rdpcap.return_value = packets

        result = self.analyzer.analyze()

        self.assertEqual(result["total_packets"], 9)
        self.assertEqual(result["top_source_ips"][0], ("192.168.1.2", 5))
        self.assertEqual(result["top_source_ips"][1], ("192.168.1.1", 3))
        self.assertEqual(result["top_destination_ips"][0], ("8.8.4.4", 5))


if __name__ == "__main__":
    unittest.main()
